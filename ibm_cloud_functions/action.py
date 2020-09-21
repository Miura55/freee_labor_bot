#
#
# main() will be run when you invoke this action
#
# @param Cloud Functions actions accept a single parameter, which must be a JSON object.
#
# @return The output of this action, which must be a JSON object.
#
from cloudant.client import Cloudant
from cloudant.document import Document
from cloudant.query import Query
from cloudant.adapters import Replay429Adapter

import requests

def main(args):
    # Connect Cloudant
    db_client = Cloudant(
        args["USERNAME"], 
        args["PASSWORD"], 
        url=args["URL"],
        adapter=Replay429Adapter(retries=10, initialBackoff=0.01)
    )
    db_client.connect()
    freee_tokens = db_client['freee_tokens']
    doc_id = args['TOKEN_DOC_ID']
    token_doc = freee_tokens.get_query_result({
        "_id": {
            "$eq": doc_id
        }
    })
    refresh_token = list(token_doc)[0]['refresh_token']
    payload = {
        'grant_type':'refresh_token',
        'refresh_token':refresh_token,
        'client_id':args['CLIENT_ID'],
        'client_secret':args['CLIENT_SECRET'],
        'redirect_uri':'urn:ietf:wg:oauth:2.0:oob'
    }
    response = requests.post(
        'https://accounts.secure.freee.co.jp/public_api/token',
        data=payload
    ).json()
    print(response)
    with Document(freee_tokens, doc_id) as document:
        document['access_token'] = response['access_token']
        document['expires_in'] = response['expires_in']
        document['refresh_token'] = response['refresh_token']
        document['created_at'] = response['created_at']
    
    return {'result':'OK!'}
