# core/anti_honeypot.py

from web3 import Web3
from config.settings import RPC_URL, PRIVATE_KEY, CHAIN_ID
from eth_account import Account

# Connect to Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Token ABI (ERC-20 standard)
ERC20_ABI = '''
[
  {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
  {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}
]
'''

# Simplified router ABI for sell test
DEX_ROUTER_ADDRESS = Web3.to_checksum_address("0xb300000b72DEAEb607a12d5f54773D1C19c7028d")

DEX_ROUTER_ABI = '''
[
  {
    "inputs": [
      {"internalType":"uint256","name":"amountIn","type":"uint256"},
      {"internalType":"uint256","name":"amountOutMin","type":"uint256"},
      {"internalType":"address[]","name":"path","type":"address[]"},
      {"internalType":"address","name":"to","type":"address"},
      {"internalType":"uint256","name":"deadline","type":"uint256"}
    ],
    "name":"swapExactTokensForETHSupportingFeeOnTransferTokens",
    "outputs":[],
    "stateMutability":"payable",
    "type":"function"
  }
]
'''

def is_safe_token(token_address):
    try:
        token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        router = w3.eth.contract(address=DEX_ROUTER_ADDRESS, abi=DEX_ROUTER_ABI)

        # Tiny approval amount
        amount_to_test = w3.toWei(0.001, 'ether')

        # Approve router to spend tokens
        approve_tx = token.functions.approve(DEX_ROUTER_ADDRESS, amount_to_test).build_transaction({
            'from': wallet_address,
            'gas': 100000,
            'gasPrice': w3.toWei('5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(wallet_address),
            'chainId': CHAIN_ID
        })

        signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed_approve.rawTransaction)

        # Sell test
        WBNB_ADDRESS = Web3.to_checksum_address("0xBB4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
        path = [Web3.to_checksum_address(token_address), WBNB_ADDRESS]
        deadline = w3.eth.get_block('latest')['timestamp'] + 1200

        sell_tx = router.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
            amount_to_test,
            0,
            path,
            wallet_address,
            deadline
        ).build_transaction({
            'from': wallet_address,
            'gas': 300000,
            'gasPrice': w3.toWei('5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(wallet_address),
            'chainId': CHAIN_ID
        })

        signed_sell = w3.eth.account.sign_transaction(sell_tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_sell.rawTransaction)

        # Wait for receipt
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        print("[✓] Honeypot test passed.")
        return True

    except Exception as e:
        print(f"[-] Honeypot detected or failed swap: {e}")
        return False
