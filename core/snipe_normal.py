# core/snipe_normal.py

from web3 import Web3
from config.settings import RPC_URL, PRIVATE_KEY, DEFAULT_SLIPPAGE, CHAIN_ID, WBNB_ADDRESS, USDT_ADDRESS
from eth_account import Account
from utils.build_tx import build_proxy_swap_tx
from utils.check_token import check_token_liquidity
import time
import json

# Factory & Router
FACTORY_ADDRESS = Web3.to_checksum_address("0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865")
FACTORY_ABI = json.loads('''[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"uint24","name":"fee","type":"uint24"},{"indexed":false,"internalType":"address","name":"pool","type":"address"}],"name":"PoolCreated","type":"event"}]''')

# Web3 Connection
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)
wallet_address = account.address
factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)

def start_normal_snipe(target_token_address, buy_amount_bnb):
    print(f"[+] Sniper armed for token: {target_token_address}")

    event_filter = factory.events.PoolCreated.create_filter(fromBlock='latest')

    while True:
        try:
            for event in event_filter.get_new_entries():
                token0 = event['args']['token0']
                token1 = event['args']['token1']
                pool_address = event['args']['pool']

                if target_token_address in [token0, token1]:
                    print(f"[+] Pool created at: {pool_address}")

                    pair_type, pool_addr = check_token_liquidity(target_token_address)
                    if pair_type:
                        print(f"[✓] Found {pair_type} pair liquidity. Executing snipe...")

                        # Build transaction
                        amount_in_wei = w3.to_wei(buy_amount_bnb, 'ether')
                        min_return_wei = int(amount_in_wei * (1 - DEFAULT_SLIPPAGE))

                        from_token = Web3.to_checksum_address(WBNB_ADDRESS)
                        to_token = Web3.to_checksum_address(target_token_address)

                        signed_tx = build_proxy_swap_tx(
                            from_token,
                            to_token,
                            amount_in_wei,
                            min_return_wei,
                            wallet_address,
                            PRIVATE_KEY
                        )

                        tx_hash = w3.eth.send_raw_transaction(signed_tx)
                        print(f"[✓] Buy transaction sent: {w3.to_hex(tx_hash)}")
                        return  # Exit after snipe

                    else:
                        print("[-] No valid WBNB/USDT pair liquidity yet.")

            time.sleep(0.3)

        except ValueError as e:
            # Re-create the filter if it gets dropped
            if 'filter not found' in str(e):
                print("[!] Filter expired — reinitializing...")
                event_filter = factory.events.PoolCreated.create_filter(fromBlock='latest')
            else:
                print(f"[!] Unexpected error: {e}")
                time.sleep(0.5)
                
