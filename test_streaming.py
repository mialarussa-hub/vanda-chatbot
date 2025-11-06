"""
Test script per verificare lo streaming del chatbot VANDA.

Testa:
1. Che il router sia registrato
2. Che lo streaming funzioni
3. Che gli spazi siano preservati
4. Le performance

Usage:
    python test_streaming.py
"""

import requests
import time
import json
from typing import Generator

# Configurazione
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/chat"

def test_health_check():
    """Testa che il server sia attivo."""
    print("=" * 80)
    print("TEST 1: Health Check")
    print("=" * 80)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server is not reachable: {e}")
        return False

def test_chat_streaming():
    """Testa lo streaming con una domanda semplice."""
    print("\n" + "=" * 80)
    print("TEST 2: Streaming Response")
    print("=" * 80)

    payload = {
        "message": "Ciao, parlami brevemente dei progetti di Vanda Designers",
        "stream": True,
        "use_rag": False  # Disabilitiamo RAG per test più veloce
    }

    print(f"\n📤 Sending request: {payload['message']}")
    print("\n📥 Streaming response:\n")

    start_time = time.time()
    chunks_received = 0
    full_response = ""
    first_chunk_time = None

    try:
        with requests.post(
            API_ENDPOINT,
            json=payload,
            stream=True,
            timeout=30
        ) as response:

            if response.status_code != 200:
                print(f"❌ Request failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                return False

            print("-" * 80)

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')

                    # Prima chunk
                    if chunks_received == 0:
                        first_chunk_time = time.time() - start_time

                    chunks_received += 1

                    # Parse SSE format
                    if line_str.startswith('data: '):
                        content = line_str[6:]  # Remove "data: "

                        if content == '[DONE]':
                            print("\n" + "-" * 80)
                            print("✅ Stream completed with [DONE] signal")
                            break
                        elif content.startswith('[ERROR]'):
                            print(f"\n❌ Error received: {content}")
                            return False
                        else:
                            # Print token
                            print(content, end='', flush=True)
                            full_response += content

            elapsed_time = time.time() - start_time

            print("\n" + "=" * 80)
            print("📊 STREAMING STATISTICS")
            print("=" * 80)
            print(f"✅ Total chunks received: {chunks_received}")
            print(f"✅ Total characters: {len(full_response)}")
            print(f"✅ First chunk time: {first_chunk_time:.2f}s")
            print(f"✅ Total time: {elapsed_time:.2f}s")
            print(f"✅ Avg speed: {chunks_received/elapsed_time:.1f} chunks/s")

            # Test spazi
            has_spaces = ' ' in full_response
            print(f"\n{'✅' if has_spaces else '❌'} Spaces preserved: {has_spaces}")

            # Test che non ci siano parole attaccate (euristico)
            words = full_response.split()
            avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
            print(f"✅ Average word length: {avg_word_length:.1f} chars")

            if avg_word_length > 15:
                print("⚠️  Warning: Average word length is high - possible missing spaces")

            return True

    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_non_streaming():
    """Testa modalità non-streaming."""
    print("\n" + "=" * 80)
    print("TEST 3: Non-Streaming Response")
    print("=" * 80)

    payload = {
        "message": "Cosa fate?",
        "stream": False,
        "use_rag": False
    }

    print(f"\n📤 Sending request: {payload['message']}")

    start_time = time.time()

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received in {elapsed_time:.2f}s")
            print(f"✅ Message length: {len(data['message'])} chars")
            print(f"✅ Session ID: {data['session_id']}")
            print(f"\n📝 Response preview:")
            print("-" * 80)
            print(data['message'][:200] + "..." if len(data['message']) > 200 else data['message'])
            print("-" * 80)
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_with_rag():
    """Testa con RAG abilitato."""
    print("\n" + "=" * 80)
    print("TEST 4: Streaming + RAG")
    print("=" * 80)

    payload = {
        "message": "Quali sono i vostri progetti più importanti?",
        "stream": True,
        "use_rag": True,
        "include_sources": False
    }

    print(f"\n📤 Sending request with RAG: {payload['message']}")
    print("\n📥 Streaming response:\n")

    start_time = time.time()
    chunks_received = 0

    try:
        with requests.post(
            API_ENDPOINT,
            json=payload,
            stream=True,
            timeout=45  # RAG può essere più lento
        ) as response:

            if response.status_code != 200:
                print(f"❌ Request failed: {response.status_code}")
                return False

            print("-" * 80)

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')

                    if line_str.startswith('data: '):
                        content = line_str[6:]
                        chunks_received += 1

                        if content == '[DONE]':
                            break
                        elif content.startswith('[ERROR]'):
                            print(f"\n❌ Error: {content}")
                            return False
                        else:
                            print(content, end='', flush=True)

            elapsed_time = time.time() - start_time

            print("\n" + "-" * 80)
            print(f"✅ RAG + Streaming completed in {elapsed_time:.2f}s")
            print(f"✅ Chunks received: {chunks_received}")

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Esegue tutti i test."""
    print("\n" + "🧪" * 40)
    print("VANDA CHATBOT - STREAMING TEST SUITE")
    print("🧪" * 40 + "\n")

    tests = [
        ("Health Check", test_health_check),
        ("Streaming Response", test_chat_streaming),
        ("Non-Streaming Response", test_chat_non_streaming),
        ("RAG + Streaming", test_chat_with_rag),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

        time.sleep(1)  # Pausa tra test

    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{'✅' if passed == total else '⚠️'} Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Your chatbot is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
