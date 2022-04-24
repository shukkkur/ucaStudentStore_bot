from hashlib import new
import re
from dotenv import load_dotenv
import os
from faunadb import query as q
from extensions import client


# update biz latest product
def update_sme_latest(biz_name):
    client.query(
        q.do(
            q.let(
                {
                    'biz_stack': q.if_(
                        q.is_empty(
                            q.match(
                                q.index("business-stack_by_name"),
                                biz_name
                            )
                        ),
                        q.create(
                            q.collection('Business_Stack'),
                            {
                                'data': {
                                    'name': biz_name,
                                    'stack': []
                                }
                            }
                        ),
                        q.get(
                            q.match(
                                q.index("business-stack_by_name"),
                                biz_name
                            )
                        )
                    )
                },
                q.let(
                    {
                        'revr_stack': q.reverse(q.select(['data', 'stack'], q.var('biz_stack')))
                    },
                    q.update(
                        # fetch sme and update the latest product
                        q.select(
                            ['ref'],
                            q.get(
                                q.match(
                                    q.index('business_by_name'),
                                    biz_name
                                )
                            )
                        ),
                        {
                            'data': {
                                'latest': q.select(
                                    [0],
                                    q.var('revr_stack')
                                )
                            }
                        }
                    )
                )
            )
        )
    )
