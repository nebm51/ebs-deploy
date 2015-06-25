
from ebs_deploy import get, parse_env_config, parse_option_settings

import boto3

def get_security_group_from_config(option_settings):
    for item in option_settings:
        if 'aws:autoscaling:launchconfiguration' in item:
            if 'SecurityGroups' in item:
                return item[2]

def get_launch_configuration_name(security_group_name):
    autoscaling = boto3.client('autoscaling')
    as_groups = autoscaling.describe_launch_configurations()

    for item in as_groups.get('LaunchConfigurations'):
        if security_group_name == item.get('SecurityGroups'):
            return item.get('LaunchConfigurationName')

def get_auto_scaling_group_name(launch_configuration_name):
    autoscaling = boto3.client('autoscaling')
    as_groups = autoscaling.describe_auto_scaling_groups()
    for item in as_groups.get('AutoScalingGroups'):
        if launch_configuration_name == item.get('LaunchConfigurationName'):
            return item.get('AutoScalingGroupName')

def disable_metrics_collection(auto_scaling_group_name):
    autoscaling = boto3.client('autoscaling')
    autoscaling.disable_metrics_collection(auto_scaling_group_name)

def enable_metrics_collection(auto_scaling_group_name):
    autoscaling = boto3.client('autoscaling')
    autoscaling.enable_metrics_collection(auto_scaling_group_name)


def add_arguments(parser):
    """
    Args for the init command
    """
    parser.add_argument('-e', '--environment',  help='Environment name', required=False, nargs='+')
    parser.add_argument('-w', '--dont-wait', help='Skip waiting for the app to be deleted', action='store_true')

def execute(helper, config, args):
    """
    Updates environments
    """
    environments = []
    if args.environment:
        for env_name in args.environment:
            environments.append(env_name)
    else:
        for env_name, env_config in get(config, 'app.environments').items():
            environments.append(env_name)

    # get data to disable metrics


    wait_environments = []
    for env_name in environments:
        env = parse_env_config(config, env_name)
        option_settings = parse_option_settings(env.get('option_settings', {}))
        security_group = get_security_group_from_config(option_settings)
        launch_configuration = get_launch_configuration_name(security_group)
        auto_scaling_group = get_auto_scaling_group_name(launch_configuration)

        disable_metrics_collection(auto_scaling_group)

        helper.update_environment(env_name,
            description=env.get('description', None),
            option_settings=option_settings,
            tier_type=env.get('tier_type'),
            tier_name=env.get('tier_name'),
            tier_version=env.get('tier_version'))
        wait_environments.append(env_name)

        enable_metrics_collection(auto_scaling_group)

    # wait
    if not args.dont_wait:
        helper.wait_for_environments(wait_environments, health='Green', status='Ready')


