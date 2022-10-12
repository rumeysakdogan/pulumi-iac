"""A Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import json

vpc = awsx.ec2.Vpc("my-vpc")

cluster = aws.ecs.Cluster("cluster")

group = aws.ec2.SecurityGroup(
    "web-secgrp",
    vpc_id=vpc.vpc_id,
    description="Enable HTTP access",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=["0.0.0.0/0"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"],
    )],
)

alb = aws.lb.LoadBalancer(
    "app-lb",
    security_groups=[group.id],
    subnets=vpc.public_subnet_ids,
)

target_group = aws.lb.TargetGroup(
    "app-tg",
    port=80,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc.vpc_id,
)

listener = aws.lb.Listener(
    "web",
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[aws.lb.ListenerDefaultActionArgs(
        type="forward",
        target_group_arn=target_group.arn,
    )],
)

role = aws.iam.Role(
    "task-exec-role",
    assume_role_policy=json.dumps({
        "Version": "2008-10-17",
        "Statement": [{
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
        }]
    }),
)

aws.iam.RolePolicyAttachment(
    "task-exec-policy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
)

task_definition = aws.ecs.TaskDefinition(
    "app-task",
    family="fargate-task-definition",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=role.arn,
    container_definitions=json.dumps([{
        "name": "my-app",
        "image": "nginx",
        "portMappings": [{
            "containerPort": 80,
            "hostPort": 80,
            "protocol": "tcp"
        }]
    }])
)

service = aws.ecs.Service(
    "app-svc",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_definition.arn,
    network_configuration={
        "assign_public_ip": "true",
        "subnets": vpc.private_subnet_ids,
        "security_groups": [group.id]
    },
    load_balancers=[{
        "target_group_arn": target_group.arn,
        "container_name": "my-app",
        "container_port": 80
    }],
    opts=pulumi.ResourceOptions(depends_on=[listener])
)

pulumi.export("url", pulumi.Output.concat(
    "http://", alb.dns_name))

