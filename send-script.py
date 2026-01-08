#!/usr/bin/env python3
"""
Script untuk terus mengirim token sampai dihentikan manual
"""

from web3 import Web3
import json
import time
import signal
import sys

# === KONFIGURASI ===
PRIVATE_KEY = ""
RPC_URL = ""
TO_ADDRESS = ""
AMOUNT = 0.0001  # Jumlah per transaksi (ubah sesuai kebutuhan)
DELAY_SECONDS = 5  # Delay antar transaksi (detik)
# ===================

# Flag untuk menghentikan loop
running = True

def signal_handler(sig, frame):
    """Tangani Ctrl+C untuk graceful shutdown"""
    global running
    print("\n\n?? Received interrupt signal. Stopping...")
    running = False

def send_transaction(w3, account, nonce):
    """Fungsi untuk mengirim satu transaksi"""
    try:
        # Konversi amount ke wei
        amount_wei = Web3.to_wei(AMOUNT, 'ether')
        
        # Cek balance
        balance = w3.eth.get_balance(account.address)
        balance_cor = Web3.from_wei(balance, 'ether')
        
        # Cek apakah balance cukup untuk transaksi + gas
        gas_price = w3.eth.gas_price
        gas_limit = 21000
        gas_cost = gas_price * gas_limit
        total_cost = amount_wei + gas_cost
        
        if balance < total_cost:
            print(f"? Balance tidak cukup! Need: {Web3.from_wei(total_cost, 'ether'):.6f} COR, Have: {balance_cor:.6f} COR")
            return None, nonce  # Return nonce yang sama karena tx gagal
        
        # Buat transaksi
        tx = {
            'nonce': nonce,
            'to': TO_ADDRESS,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id,
        }
        
        # Estimasi gas
        try:
            gas_estimate = w3.eth.estimate_gas(tx)
            tx['gas'] = gas_estimate
        except Exception as e:
            print(f"??  Gas estimation failed: {e}")
        
        # Sign dan kirim
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"? TX #{nonce} Sent! Hash: {tx_hash.hex()[:20]}...")
        print(f"   Amount: {AMOUNT} COR | Gas: {Web3.from_wei(gas_price, 'gwei'):.2f} Gwei")
        
        # Increment nonce untuk transaksi berikutnya
        return tx_hash.hex(), nonce + 1
        
    except Exception as e:
        print(f"? Error sending transaction: {e}")
        return None, nonce

def main():
    global running
    
    # Setup signal handler untuk Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("?? COR AUTO SENDER")
    print("=" * 60)
    print(f"?? Sender: {Web3().eth.account.from_key(PRIVATE_KEY).address}")
    print(f"?? Receiver: {TO_ADDRESS}")
    print(f"?? Amount per TX: {AMOUNT} COR")
    print(f"??  Delay: {DELAY_SECONDS} seconds")
    print(f"??  Press Ctrl+C to stop")
    print("=" * 60)
    
    # Setup Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Cek koneksi
    if not w3.is_connected():
        print("? Tidak bisa connect ke RPC")
        return
    
    print(f"? Connected! Chain ID: {w3.eth.chain_id}")
    print(f"? Current Block: {w3.eth.block_number}")
    
    # Dapatkan address dari private key
    account = w3.eth.account.from_key(PRIVATE_KEY)
    
    # Cek balance awal
    balance = w3.eth.get_balance(account.address)
    balance_cor = Web3.from_wei(balance, 'ether')
    print(f"?? Starting Balance: {balance_cor:.6f} COR")
    print("-" * 60)
    
    # Dapatkan nonce awal
    initial_nonce = w3.eth.get_transaction_count(account.address)
    current_nonce = initial_nonce
    tx_count = 0
    
    print(f"?? Starting nonce: {current_nonce}")
    print("\n??  Starting transaction loop...\n")
    
    # Main loop
    try:
        while running:
            # Kirim transaksi
            tx_hash, new_nonce = send_transaction(w3, account, current_nonce)
            
            if tx_hash:
                tx_count += 1
                current_nonce = new_nonce
                
                # Update balance
                if tx_count % 5 == 0:  # Update balance setiap 5 transaksi
                    balance = w3.eth.get_balance(account.address)
                    balance_cor = Web3.from_wei(balance, 'ether')
                    print(f"?? Balance update: {balance_cor:.6f} COR")
                
                # Tampilkan explorer link
                if tx_count == 1:  # Hanya tampilkan untuk transaksi pertama
                    print(f"?? Explorer: https://explorer/tx/{tx_hash}")
            else:
                # Jika gagal, tunggu lebih lama sebelum mencoba lagi
                print(f"? Waiting {DELAY_SECONDS * 2} seconds before retry...")
                time.sleep(DELAY_SECONDS * 2)
                continue
            
            # Delay sebelum transaksi berikutnya
            if running and tx_count > 0:
                print(f"? Next transaction in {DELAY_SECONDS} seconds...")
                for i in range(DELAY_SECONDS):
                    if not running:
                        break
                    time.sleep(1)
                    if i % 5 == 0 and i > 0:
                        print(f"   {i}/{DELAY_SECONDS} seconds...")
    
    except KeyboardInterrupt:
        print("\n?? Keyboard interrupt received.")
    except Exception as e:
        print(f"\n? Unexpected error: {e}")
    finally:
        running = False
    
    # Tampilkan statistik akhir
    print("\n" + "=" * 60)
    print("?? FINAL STATISTICS")
    print("=" * 60)
    print(f"? Total transactions sent: {tx_count}")
    print(f"?? Starting nonce: {initial_nonce}")
    print(f"?? Final nonce: {current_nonce}")
    
    # Cek balance akhir
    try:
        final_balance = w3.eth.get_balance(account.address)
        final_balance_cor = Web3.from_wei(final_balance, 'ether')
        
        print(f"?? Starting balance: {Web3.from_wei(balance, 'ether'):.6f} COR")
        print(f"?? Final balance: {final_balance_cor:.6f} COR")
        
        total_spent = (balance - final_balance) if final_balance < balance else 0
        print(f"?? Total spent: {Web3.from_wei(total_spent, 'ether'):.6f} COR")
    except:
        print("??  Could not retrieve final balance")
    
    print("\n?? Program stopped.")
    print("=" * 60)

if __name__ == "__main__":
    main()
