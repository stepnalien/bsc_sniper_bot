from web3 import Web3
from config.settings import RPC_URL, FACTORY_ADDRESS, WBNB_ADDRESS, USDT_ADDRESS
import requests
import json

w3 = Web3(Web3.HTTPProvider(RPC_URL))

FACTORY_ABI = json.loads("""
[
    {
        "inputs": [
            {"internalType": "address","name": "tokenA","type": "address"},
            {"internalType": "address","name": "tokenB","type": "address"},
            {"internalType": "uint24","name": "fee","type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address","name": "pool","type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]
""")

factory_contract = w3.eth.contract(address=Web3.to_checksum_address(FACTORY_ADDRESS), abi=FACTORY_ABI)

def get_token_info(contract):
    try:
        response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{contract}")
        data = response.json()

        if not data.get('pairs'):
            return None  # no market data yet

        pair = data['pairs'][0]
        return {
            'name': pair['baseToken']['name'],
            'symbol': pair['baseToken']['symbol'],
            'liquidity': float(pair['liquidity']['base']) if 'base' in pair['liquidity'] else 0
        }
    except Exception as e:
        print(f"Error fetching token info: {e}")
        return None

def check_token_liquidity(token_address, fee=2500):
    token_address = Web3.to_checksum_address(token_address)

    pool_wbnb = factory_contract.functions.getPool(token_address, Web3.to_checksum_address(WBNB_ADDRESS), fee).call()
    if pool_wbnb != '0x0000000000000000000000000000000000000000':
        return 'WBNB', pool_wbnb

    pool_usdt = factory_contract.functions.getPool(token_address, Web3.to_checksum_address(USDT_ADDRESS), fee).call()
    if pool_usdt != '0x0000000000000000000000000000000000000000':
        return 'USDT', pool_usdt

    return None, None
