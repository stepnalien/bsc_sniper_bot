from web3 import Web3
import json
from config.settings import RPC_URL, CHAIN_ID, PRIVATE_KEY

# Web3 connection
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Derive wallet address from private key
account = w3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Router setup
ROUTER_ADDRESS = Web3.to_checksum_address("0x5efc784D444126ECc05f22c49FF3FBD7D9F4868a")
ROUTER_ABI = json.loads('''
[
  {
    "inputs": [
      {"internalType": "address", "name": "router", "type": "address"},
      {"internalType": "uint256", "name": "fromTokenWithFee", "type": "uint256"},
      {"internalType": "uint256", "name": "fromAmt", "type": "uint256"},
      {"internalType": "uint256", "name": "toTokenWithFee", "type": "uint256"},
      {"internalType": "uint256", "name": "minReturnAmt", "type": "uint256"},
      {"internalType": "bytes", "name": "callData", "type": "bytes"}
    ],
    "name": "proxySwapV2",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  }
]
''')

router = w3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)

def build_proxy_swap_tx(router_address, from_token_with_fee, amount_in, to_token_with_fee, min_return_amt, calldata):
    nonce = w3.eth.get_transaction_count(wallet_address)

    tx = router.functions.proxySwapV2(
        router_address,
        from_token_with_fee,
        amount_in,
        to_token_with_fee,
        min_return_amt,
        calldata
    ).build_transaction({
        'from': wallet_address,
        'value': amount_in,  # Assuming BNB being sent as 'fromAmt'
        'gas': 400000,
        'gasPrice': w3.to_wei('3', 'gwei'),
        'nonce': nonce,
        'chainId': CHAIN_ID
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    return signed_tx.rawTransaction

def send_proxy_swap_tx(token_address, buy_amount_bnb, slippage_percent):
    try:
        # Native BNB address representation in your router
        from_token = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
        to_token = Web3.to_checksum_address(token_address)

        amount_in = w3.to_wei(buy_amount_bnb, 'ether')
        min_return = int(amount_in * (1 - (slippage_percent / 100)))

        # Convert addresses to uint256 for proxySwapV2
        from_token_with_fee = int(Web3.to_int(Web3.to_bytes(hexstr=from_token)))
        to_token_with_fee = int(Web3.to_int(Web3.to_bytes(hexstr=to_token)))

        # Call data can be empty if router is handling native swap internally
        calldata = b''

        raw_tx = build_proxy_swap_tx(
            ROUTER_ADDRESS,
            from_token_with_fee,
            amount_in,
            to_token_with_fee,
            min_return,
            calldata
        )

        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        print(f"[✓] Swap Tx Sent: {tx_hash.hex()}")

        return tx_hash.hex()

    except Exception as e:
        print(f"[❌] Transaction Error: {e}")
        return None
