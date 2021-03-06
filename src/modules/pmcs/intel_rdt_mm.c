/*
 *  intel_rdt_mm.c
 *
 *  PMCTrack monitoring module that provides support for
 * 	Intel Cache Monitoring Technology (CMT) and Intel Memory Bandwidth
 *  Monitoring (MBM)
 *
 *  Copyright (c) 2015 Juan Carlos Saez <jcsaezal@ucm.es>
 *
 *  This code is licensed under the GNU GPL v2.
 */

#include <pmc/hl_events.h>
#include <pmc/mc_experiments.h>
#include <pmc/monitoring_mod.h>
#include <pmc/intel_rdt.h>
#include <pmc/intel_rapl.h>
#include <pmc/edp.h>

#include <asm/atomic.h>
#include <asm/topology.h>
#include <linux/ftrace.h>

#define INTEL_CMT_MODULE_STR "PMCtrack module that supports Intel CMT"


static intel_cmt_support_t cmt_support;
static intel_cat_support_t cat_support;
static intel_mba_support_t mba_support;
static intel_rapl_support_t* rapl_support=NULL;

/* Configuration parameters for this monitoring module */
static struct {
	rmid_allocation_policy_t rmid_allocation_policy; /* Selected RMID allocation policy */
	unsigned char use_rapl_counters;
	unsigned char reset_on_cswitch;
	unsigned char force_ebs_counters;
}
intel_cmt_config= {RMID_FIFO,0,0,0};

/* Per-thread private data for this monitoring module */
typedef struct {
	unsigned char first_time;
	intel_cmt_thread_struct_t cmt_data;
	intel_rapl_control_t rapl_ctrl;
	uint64_t instr_counter;		/* Global instruction counter to compute the EDP */
	uint_t security_id;
} intel_cmt_thread_data_t;


static core_experiment_set_t ebs_sampling_pmc_configuration;

static const char* ebs_sampling_pmcstr_cfg[]= {
	"pmc0,ebs0,pmc1",
	NULL
};



/* Return the capabilities/properties of this monitoring module */
static void intel_cmt_module_counter_usage(monitoring_module_counter_usage_t* usage)
{
	if (intel_cmt_config.use_rapl_counters) {
		int i;
		usage->hwpmc_mask=0;
		usage->nr_virtual_counters=rapl_support->nr_available_power_domains; // Three domains energy usage
		usage->nr_experiments=0;
		for (i=0; i<usage->nr_virtual_counters; i++)
			usage->vcounter_desc[i]=rapl_support->available_vcounters[i];
	} else {
		usage->hwpmc_mask=0;
		usage->nr_virtual_counters=CMT_MAX_EVENTS; // L3_USAGE, L3_TOTAL_BW, L3_LOCAL_BW
		usage->nr_experiments=0;
		usage->vcounter_desc[0]="llc_usage";
		usage->vcounter_desc[1]="total_llc_bw";
		usage->vcounter_desc[2]="local_llc_bw";
	}
}


/* MM initialization function */
static int intel_cmt_enable_module(void)
{
	int retval=0;

	if (configure_performance_counters_set(ebs_sampling_pmcstr_cfg, &ebs_sampling_pmc_configuration, 1)) {
		printk("Can't configure global performance counters. This is too bad ... ");
		return -EINVAL;
	}

	if ((retval=intel_cmt_initialize(&cmt_support)))
		return retval;

	if ((retval=intel_cat_initialize(&cat_support))) {
		intel_cmt_release(&cmt_support);
		return retval;
	}

	if ((retval=edp_initialize_environment())) {
		intel_cat_release(&cat_support);
		intel_cmt_release(&cmt_support);
		return retval;
	}

	rapl_support=get_global_rapl_handler();

	intel_mba_initialize(&mba_support);

	return 0;
}

/* MM cleanup function */
static void intel_cmt_disable_module(void)
{
	intel_cmt_release(&cmt_support);
	intel_cat_release(&cat_support);
	intel_mba_release(&mba_support);
	edp_release_resources();
	rapl_support=NULL;

	free_experiment_set(&ebs_sampling_pmc_configuration);

	printk(KERN_ALERT "%s monitoring module unloaded!!\n",INTEL_CMT_MODULE_STR);
}


static int intel_cmt_on_read_config(char* str, unsigned int len)
{
	char* dest=str;
	dest+=sprintf(dest,"rmid_alloc_policy=%d (%s)\n",
	              intel_cmt_config.rmid_allocation_policy,
	              rmid_allocation_policy_str[intel_cmt_config.rmid_allocation_policy]);
	dest+=sprintf(dest,"cat_nr_cos_available=%d\n",
	              cat_support.cat_nr_cos_available);
	dest+=sprintf(dest,"cat_cbm_length=%d\n",
	              cat_support.cat_cbm_length);

	if (mba_support.mba_is_supported) {
		dest+=sprintf(dest,"mba_max_delay=%d\n",
		              mba_support.mba_max_throtling);
		dest+=sprintf(dest,"mba_cos_available=%d\n",
		              mba_support.mba_nr_cos_available);
		dest+=sprintf(dest,"mba_linear_throttling=%d\n",
		              mba_support.mba_is_linear);
	}
	dest+=intel_cat_print_capacity_bitmasks(dest,&cat_support);
	dest+=intel_mba_print_delay_values(dest,&mba_support);
	dest+=sprintf(dest,"force_ebs_counters=%u\n",
	              intel_cmt_config.force_ebs_counters);
	dest+=sprintf(dest,"use_rapl_counters=%u\n",
	              intel_cmt_config.use_rapl_counters);
	dest+=edp_dump_global_counters(dest);
	return dest-str;
}

//

static int intel_cmt_on_write_config(const char *str, unsigned int len)
{
	int val;
	unsigned int uval;
	unsigned int mask=0;

	if (sscanf(str,"rmid_alloc_policy %i",&val)==1 && val>=0 && val<NR_RMID_ALLOC_POLICIES) {
		intel_cmt_config.rmid_allocation_policy=val;
		set_cmt_policy(intel_cmt_config.rmid_allocation_policy);
	} else if (sscanf(str,"cos_id=%i",&val)==1 &&
	           (val>=0 && val<cat_support.cat_nr_cos_available)) {
		pmon_prof_t* prof=current->pmc;
		intel_cmt_thread_data_t*  data;

		if (!prof || !prof->monitoring_mod_priv_data)
			return -EINVAL;

		/* Setup cosid !! */
		data=prof->monitoring_mod_priv_data;
		data->cmt_data.cos_id=val;
		printk(KERN_ALERT "Setting COSID=%d for process %d\n",data->cmt_data.cos_id,current->tgid);
	} else if (sscanf(str,"llc_cbm%i 0x%x",&val,&mask)==2) {
		intel_cat_set_capacity_bitmask(&cat_support,val,mask);
	} else if (sscanf(str,"mba_delay%i %u",&val,&uval)==2) {
		intel_mba_set_delay_values(&mba_support,val,uval);
	} else if (sscanf(str,"force_ebs_counters %u",&uval)==1) {
		intel_cmt_config.force_ebs_counters=uval;
	} else if (sscanf(str,"use_rapl_counters %u",&uval)==1 &&  (uval==0 || uval==1) ) {
		intel_cmt_config.use_rapl_counters=uval;
	} else if (strncmp(str,"restart_edp",11)==0) {
		printk(KERN_INFO "Resetting global EDP counters\n");
		edp_reset_global_counters();
		return len;
	} else if (strncmp(str,"pause_edp",9)==0) {
		printk(KERN_INFO "Pause global EDP counts\n");
		edp_pause_global_counts();
		return len;
	} else if (strncmp(str,"resume_edp",10)==0) {
		printk(KERN_INFO "Resume global EDP counts\n");
		edp_resume_global_counts();
		return len;
	}
	return len;
}

/* on fork() callback */
static int intel_cmt_on_fork(unsigned long clone_flags, pmon_prof_t* prof)
{
	intel_cmt_thread_data_t*  data=NULL;

	if (prof->monitoring_mod_priv_data!=NULL)
		return 0;

	data= kmalloc(sizeof (intel_cmt_thread_data_t), GFP_KERNEL);

	if (data == NULL)
		return -ENOMEM;

	initialize_cmt_thread_struct(&data->cmt_data);

	if (is_new_thread(clone_flags) && current->pmc) {
		pmon_prof_t *pprof= (pmon_prof_t*)current->pmc;
		intel_cmt_thread_data_t* parent_data=pprof->monitoring_mod_priv_data;
		data->first_time=0;
		data->cmt_data.rmid=parent_data->cmt_data.rmid;
		use_rmid(parent_data->cmt_data.rmid); /* Increase ref counter */
		trace_printk("Assigned RMID::%u\n",data->cmt_data.rmid);
	} else {
		data->first_time=1;
		data->cmt_data.rmid=0; /* It will be assigned in the first context switch */
	}

	intel_rapl_control_init(&data->rapl_ctrl);

	if (!intel_cmt_config.reset_on_cswitch)
		intel_rapl_update_energy_values_thread(rapl_support,&data->rapl_ctrl,0);

	/* EBS functionality: Configure counters (if counters were not already forced by the user) */
	if (!prof->pmcs_config && intel_cmt_config.force_ebs_counters) {
		clone_core_experiment_set_t(&prof->pmcs_multiplex_cfg[0],&ebs_sampling_pmc_configuration);

		prof->pmcs_config=get_cur_experiment_in_set(&prof->pmcs_multiplex_cfg[0]);

		/* Activate EBS MODE if necessary */
		if (prof->pmcs_config->ebs_idx!=-1)
			prof->profiling_mode=EBS_SCHED_MODE;
	}

	data->instr_counter=0;
	data->security_id=current_monitoring_module_security_id();
	prof->monitoring_mod_priv_data = data;
	return 0;
}

/* on exec() callback */
static void intel_cmt_on_exec(pmon_prof_t* prof) { }

/*
 * Read the LLC occupancy and cumulative memory bandwidth counters
 * and set the associated virtual counts in the PMC sample structure
 */
static int intel_cmt_on_new_sample(pmon_prof_t* prof,int cpu,pmc_sample_t* sample,int flags,void* data)
{
	intel_cmt_thread_data_t* tdata=prof->monitoring_mod_priv_data;
	uint_t llc_id=topology_physical_package_id(cpu),i=0;
	int cnt_virt=0;
	intel_rdt_event_t* global_mbm_events;
	uint64_t total_bw;
	unsigned int rmid_count;

	intel_rapl_sample_t rapl_sample;
	int active_domains=0;


	if (tdata==NULL)
		return 0;

	/*
	 * Update global instruction counter to measure EDP.
	 * Important assumption -> instructions are always counted
	 * with the first PMC in the set (logical counter #0)
	 */
	tdata->instr_counter+=sample->pmc_counts[0];

	//if (flags & MM_EXIT)
	//	edp_update_global_instr_counter(&tdata->instr_counter);


	if (intel_cmt_config.use_rapl_counters) {
		if (!intel_cmt_config.reset_on_cswitch || !(flags & MM_NO_CUR_CPU))
			intel_rapl_update_energy_values_thread(rapl_support,&tdata->rapl_ctrl,1);

		intel_rapl_get_energy_sample_thread(rapl_support,&tdata->rapl_ctrl,&rapl_sample);

		for (i=0; i<RAPL_NR_DOMAINS; i++) {
			if (rapl_support->available_power_domains_mask & (1<<i)) {
				if ((prof->virt_counter_mask & (1<<active_domains)) ) { // Just one virtual counter
					sample->virt_mask|=(1<<active_domains);
					sample->nr_virt_counts++;
					sample->virtual_counts[cnt_virt]=rapl_sample.energy_value[i];
					cnt_virt++;
				}
				active_domains++;
			}
		}

	} else {

		if (tdata->first_time)
			return 0;

		intel_cmt_update_supported_events(&cmt_support,&tdata->cmt_data,llc_id);

		/* Patch global data with actual aggregate counts if virt1 enabled */
		if (prof->virt_counter_mask & 0x2) {
			global_mbm_events=intel_rdt_syswide_read_localbw(&cmt_support,llc_id,&rmid_count,&total_bw);
			tdata->cmt_data.last_llc_utilization[llc_id][1]=total_bw;
		}

		/* Embed virtual counter information so that the user can see what's going on */
		for(i=0; i<CMT_MAX_EVENTS; i++) {
			if ((prof->virt_counter_mask & (1<<i) )) {
				sample->virt_mask|=(1<<i);
				sample->nr_virt_counts++;
				sample->virtual_counts[cnt_virt]=tdata->cmt_data.last_llc_utilization[llc_id][i];
				cnt_virt++;
			}
		}
	}

	return 0;
}

static void intel_cmt_on_migrate(pmon_prof_t* prof, int prev_cpu, int new_cpu) { }

/* on exit() callback -> return RMID to the pool */
static void intel_cmt_on_exit(pmon_prof_t* prof)
{
	intel_cmt_thread_data_t* data=(intel_cmt_thread_data_t*)prof->monitoring_mod_priv_data;
	if (data)
		put_rmid(data->cmt_data.rmid);

	if (prof->this_tsk->prof_enabled)
		edp_update_global_instr_counter(&data->instr_counter);
}

/* Free up private data */
static void intel_cmt_on_free_task(pmon_prof_t* prof)
{
	if (prof->monitoring_mod_priv_data)
		kfree(prof->monitoring_mod_priv_data);
}

/* on switch_in callback */
static void intel_cmt_on_switch_in(pmon_prof_t* prof)
{
	intel_cmt_thread_data_t* data=(intel_cmt_thread_data_t*)prof->monitoring_mod_priv_data;
	int was_first_time=0;

	if (!data)
		return;

	if (data->first_time && data->security_id==current_monitoring_module_security_id()) {
		// Assign RMID
		data->cmt_data.rmid=get_rmid();
		data->first_time=0;
		was_first_time=0;
#ifdef DEBUG
		trace_printk("Assigned RMID::%u\n",data->cmt_data.rmid);
#endif
	}

	__set_rmid_and_cos(data->cmt_data.rmid,data->cmt_data.cos_id);

	if (was_first_time) {
		uint_t llc_id=topology_physical_package_id(smp_processor_id());
		intel_cmt_update_supported_events(&cmt_support,&data->cmt_data,llc_id);
	}

	/* Update prev counts */
	if (intel_cmt_config.reset_on_cswitch)
		intel_rapl_update_energy_values_thread(rapl_support,&data->rapl_ctrl,0);
}

/* on switch_out callback */
static void intel_cmt_on_switch_out(pmon_prof_t* prof)
{
	intel_cmt_thread_data_t* data=(intel_cmt_thread_data_t*)prof->monitoring_mod_priv_data;

	__unset_rmid();

	/* Accumulate energy readings */
	if (!data->first_time && intel_cmt_config.reset_on_cswitch)
		intel_rapl_update_energy_values_thread(rapl_support,&data->rapl_ctrl,1);
}

/* Modify this function if necessary to expose CMT/MBM information to the OS scheduler */
static int intel_cmt_get_current_metric_value(pmon_prof_t* prof, int key, uint64_t* value)
{
	return -1;
}


/* Implementation of the monitoring_module_t interface */
monitoring_module_t intel_rdt_mm= {
	.info=INTEL_CMT_MODULE_STR,
	.id=-1,
	.probe_module=intel_cmt_probe,
	.enable_module=intel_cmt_enable_module,
	.disable_module=intel_cmt_disable_module,
	.on_read_config=intel_cmt_on_read_config,
	.on_write_config=intel_cmt_on_write_config,
	.on_fork=intel_cmt_on_fork,
	.on_exec=intel_cmt_on_exec,
	.on_new_sample=intel_cmt_on_new_sample,
	.on_migrate=intel_cmt_on_migrate,
	.on_exit=intel_cmt_on_exit,
	.on_free_task=intel_cmt_on_free_task,
	.on_switch_in=intel_cmt_on_switch_in,
	.on_switch_out=intel_cmt_on_switch_out,
	.get_current_metric_value=intel_cmt_get_current_metric_value,
	.module_counter_usage=intel_cmt_module_counter_usage
};
