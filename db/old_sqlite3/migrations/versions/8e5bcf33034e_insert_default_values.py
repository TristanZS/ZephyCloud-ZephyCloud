# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Insert default values

Revision ID: 8e5bcf33034e
Revises: 1e54e6f3375f
Create Date: 2018-05-07 22:22:04.315349

"""

from alembic import op
import math
import os
import json

# Revision identifiers, used by Alembic.
revision = '8e5bcf33034e'
down_revision = '1e54e6f3375f'
branch_labels = None
depends_on = None


# Default values constants
RANK_BRONZE = 1
RANK_SILVER = 2
RANK_GOLD = 3
RANK_ROOT = 4

AWS_GRANULARITY = 1
AWS_MIN_GRANULARITY = 60
ZEPHYCLOUD_GRANULARITY = 300

FIX_PRICES = {
    "anal": 0.10,
    "mesh": 0.05,
    "calc": 0.05,
    "rose": 0.05,
    "extra": 0.05,
    "assess": 0.05,
}

CLUSTER_LIMITS = {
    "anal": 1,
    "mesh": 1,
    "calc": 20,
    "rose": 1,
    "extra": 1,
    "assess": 1,
}

NEW_USERS = [{'login': 'tristan', 'pwd': 'tristan', 'rank': 3},
             {'login': 'sam', 'pwd': 'sam', 'rank': 3}]

AWS_WEST_MACHINES = {
    "c5.xlarge": {
        "cpu": 4,
        "ram": 8,
        "available": 400
    },
    "c5.2xlarge": {
        "cpu": 8,
        "ram": 16,
        "available": 400
    },
    "c5.4xlarge": {
        "cpu": 16,
        "ram": 32,
        "available": 400
    },
    "c5.9xlarge": {
        "cpu": 36,
        "ram": 72,
        "available": 400
    },
    "c5.18xlarge": {
        "cpu": 72,
        "ram": 144,
        "available": 400
    }
}

AWS_WEST_OLD_MACHINES = {
    "c4.xlarge": {
        "cpu": 4,
        "ram": 7.5,
        "available": 400
    },
    "c4.2xlarge": {
        "cpu": 8,
        "ram": 15,
        "available": 400
    },
    "c4.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c4.8xlarge": {
        "cpu": 36,
        "ram": 60,
        "available": 400
    },
    "x1.16xlarge": {
        "cpu": 64,
        "ram": 976,
        "available": 10
    }
}

AWS_WEST_VERY_OLD_MACHINES = {
    "c3.xlarge": {
        "cpu": 4,
        "ram": 7.5,
        "available": 400
    },
    "c3.2xlarge": {
        "cpu": 8,
        "ram": 15,
        "available": 400
    },
    "c3.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c3.8xlarge": {
        "cpu": 32,
        "ram": 60,
        "available": 400
    }
}

# aws_eu_old

AWS_CHINA_MACHINES = {
    "c4.2xlarge": {
        "cpu": 4,
        "ram": 15,
        "available": 400
    },
    "c4.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c4.8xlarge": {
        "cpu": 36,
        "ram": 60,
        "available": 400
    },
    "x1.16xlarge": {
        "cpu": 64,
        "ram": 976,
        "available": 10
    }
}

# prices are in dollar per hour
COST_PER_HOUR_EU = {
    "c5.xlarge": 0.192,
    "c5.2xlarge": 0.384,
    "c5.4xlarge": 0.768,
    "c5.9xlarge": 1.728,
    "c5.18xlarge": 3.456,
    "c4.xlarge": 0.226,
    "c4.2xlarge": 0.453,
    "c4.4xlarge": 0.905,
    "c4.8xlarge": 1.811,
    "x1.16xlarge": 8.003,
    "c3.xlarge": 0.239,
    "c3.2xlarge": 0.478,
    "c3.4xlarge": 0.956,
    "c3.8xlarge": 1.912
}

# prices are in yuan per hour
COST_PER_HOUR_CN = {
    "c4.2xlarge": 4.535,
    "c4.4xlarge": 9.071,
    "c4.8xlarge": 18.141,
    "x1.16xlarge": 137.752
}


SECURITY_MARGIN = 0.05
DONATION_RATIO = 0.05
DOLLAR_TO_EURO = 0.85
YUAN_TO_EURO = 0.13
WEST_PRICE = 4
CHINA_PRICE = 30

WEST_MARGIN = {
    'root': 1,
    'gold': 2,
    'silver': 4,
    'bronze': 10
}
CHINA_MARGIN = {
    'root': 1,
    'gold': 2,
    'silver': 10,
    'bronze': 30
}

DOCKER_MACHINES = {
    "docker": {
        "cpu": 2,
        "ram": 1,
        "available": 10
    },
    "docker_2": {
        "cpu": 4,
        "ram": 2,
        "available": 10
    }
}

# Fake dollar per hour
COST_PER_HOUR_DOCKER = {
    "docker": 0.192,
    "docker_2": 0.384,
}


def upgrade():
    import core.api_util
    import models.users
    import models.provider_config

    for user in NEW_USERS:
        if models.users.get_user(login=user['login']) is not None:
            continue
        user_db = models.users.create_user(user["login"], user["pwd"], user["rank"])
        models.users.add_user_credits(core.api_util.price_from_float(500), user_db['id'], "Initial credit for users")

    if "MIGRATION_PROVIDERS" in os.environ and os.environ["MIGRATION_PROVIDERS"].strip():
        providers = json.loads(os.environ["MIGRATION_PROVIDERS"].strip())
    else:
        providers = ["docker_local"]

    if "aws_eu" in providers:
        for machine, details in AWS_WEST_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            models.provider_config.set_machine("aws_eu", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            models.provider_config.set_machine("aws_eu_spot", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               int(math.ceil(float(cost)/2)), core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            if machine not in COST_PER_HOUR_EU.keys():
                continue
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in models.users.all_ranks():
                rank_str = models.users.rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                models.provider_config.set_machine_price("aws_eu", machine, rank, price, ZEPHYCLOUD_GRANULARITY)
                models.provider_config.set_machine_price("aws_eu_spot", machine, rank, math.ceil(price / 2),
                                                         ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            models.provider_config.set_operation_cost("aws_eu", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu", operation, AWS_WEST_MACHINES.keys())
            models.provider_config.set_operation_cost("aws_eu_spot", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu_spot", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu_spot", operation, AWS_WEST_MACHINES.keys())

    if "aws_eu_old" in providers:
        for machine, details in AWS_WEST_OLD_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            models.provider_config.set_machine("aws_eu_old", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            models.provider_config.set_machine("aws_eu_old_spot", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               int(math.ceil(float(cost)/2)), core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in models.users.all_ranks():
                rank_str = models.users.rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                models.provider_config.set_machine_price("aws_eu_old", machine, rank, price, ZEPHYCLOUD_GRANULARITY)
                models.provider_config.set_machine_price("aws_eu_old_spot", machine, rank, math.ceil(price/2),
                                                         ZEPHYCLOUD_GRANULARITY)
        for operation, price in FIX_PRICES.items():
            models.provider_config.set_operation_cost("aws_eu_old", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu_old", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu_old", operation, AWS_WEST_OLD_MACHINES.keys())
            models.provider_config.set_operation_cost("aws_eu_old_spot", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu_old_spot", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu_old_spot", operation, AWS_WEST_OLD_MACHINES.keys())

    if "aws_eu_very_old" in providers:
        for machine, details in AWS_WEST_VERY_OLD_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            models.provider_config.set_machine("aws_eu_very_old", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            models.provider_config.set_machine("aws_eu_very_old_spot", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               int(math.ceil(float(cost)/2)), core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in models.users.all_ranks():
                rank_str = models.users.rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                models.provider_config.set_machine_price("aws_eu_very_old", machine, rank, price, ZEPHYCLOUD_GRANULARITY)
                models.provider_config.set_machine_price("aws_eu_very_old_spot", machine, rank, math.ceil(price/2),
                                                         ZEPHYCLOUD_GRANULARITY)
        for operation, price in FIX_PRICES.items():
            models.provider_config.set_operation_cost("aws_eu_very_old", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu_very_old", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu_very_old", operation, AWS_WEST_VERY_OLD_MACHINES.keys())
            models.provider_config.set_operation_cost("aws_eu_very_old_spot", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_eu_very_old_spot", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_eu_very_old_spot", operation, AWS_WEST_VERY_OLD_MACHINES.keys())

    if "aws_cn"in providers:
        for machine, details in AWS_CHINA_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_CN[machine] / 3600)
            models.provider_config.set_machine("aws_cn", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_YUAN,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_CN[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in models.users.all_ranks():
                rank_str = models.users.rank_to_str(rank)
                if rank_str not in CHINA_MARGIN:
                    pass
                float_price = ref_price * float(CHINA_MARGIN[rank_str]) * YUAN_TO_EURO / float(CHINA_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                models.provider_config.set_machine_price("aws_cn", machine, rank, price, ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            models.provider_config.set_operation_cost("aws_cn", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("aws_cn", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("aws_cn", operation, AWS_WEST_MACHINES.keys())

    if "docker_local" in providers:
        for machine, details in DOCKER_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_DOCKER[machine] / 3600)
            models.provider_config.set_machine("docker_local", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR, AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_DOCKER[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in models.users.all_ranks():
                rank_str = models.users.rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                models.provider_config.set_machine_price("docker_local", machine, rank, price, ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            models.provider_config.set_operation_cost("docker_local", operation, core.api_util.price_from_float(price))
            models.provider_config.set_operation_cluster_limit("docker_local", operation, CLUSTER_LIMITS[operation])
            models.provider_config.set_operation_machines("docker_local", operation, DOCKER_MACHINES.keys())


def downgrade():
    conn = op.get_bind()
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM machines")
    conn.execute("DELETE FROM machines_history")
    conn.execute("DELETE FROM operation_machine")
    conn.execute("DELETE FROM machine_prices")
    conn.execute("DELETE FROM machine_prices_history")
