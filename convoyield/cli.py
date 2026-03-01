"""
ConvoYield CLI — Command-line interface for the entire ecosystem.

Usage:
    python -m convoyield demo              Run the interactive demo
    python -m convoyield server             Start the Cloud API server
    python -m convoyield dashboard          Open the analytics dashboard
    python -m convoyield analyze <file>     Analyze a conversation log file
    python -m convoyield register           Register for a Cloud API key
    python -m convoyield playbooks          List available premium playbooks
    python -m convoyield status             Check system status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="convoyield",
        description="ConvoYield — Conversational Yield Optimization Engine",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── demo ──────────────────────────────────────────────────
    subparsers.add_parser("demo", help="Run the interactive demo")

    # ── server ────────────────────────────────────────────────
    server_p = subparsers.add_parser("server", help="Start the Cloud API server")
    server_p.add_argument("--port", type=int, default=8000)
    server_p.add_argument("--host", default="0.0.0.0")

    # ── analyze ───────────────────────────────────────────────
    analyze_p = subparsers.add_parser("analyze", help="Analyze a conversation log")
    analyze_p.add_argument("file", help="JSON file with conversation logs")
    analyze_p.add_argument("--base-value", type=float, default=25.0)

    # ── register ──────────────────────────────────────────────
    register_p = subparsers.add_parser("register", help="Register for a Cloud API key")
    register_p.add_argument("--email", required=True)
    register_p.add_argument("--server", default="http://localhost:8000")

    # ── playbooks ─────────────────────────────────────────────
    subparsers.add_parser("playbooks", help="List available premium playbooks")

    # ── status ────────────────────────────────────────────────
    status_p = subparsers.add_parser("status", help="Check system status")
    status_p.add_argument("--server", default="http://localhost:8000")

    # ── interactive ───────────────────────────────────────────
    subparsers.add_parser("interactive", help="Interactive conversation mode")

    args = parser.parse_args()

    if args.command == "demo":
        _run_demo()
    elif args.command == "server":
        _run_server(args.host, args.port)
    elif args.command == "analyze":
        _run_analyze(args.file, args.base_value)
    elif args.command == "register":
        _run_register(args.email, args.server)
    elif args.command == "playbooks":
        _list_playbooks()
    elif args.command == "status":
        _check_status(args.server)
    elif args.command == "interactive":
        _run_interactive()
    else:
        parser.print_help()
        _print_banner()


def _print_banner():
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║       ConvoYield v1.0.0                         ║")
    print("  ║       Conversational Yield Optimization Engine   ║")
    print("  ║                                                  ║")
    print("  ║  Every conversation is a financial instrument.   ║")
    print("  ║  We help you maximize its yield.                 ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    print("  Commands:")
    print("    convoyield demo          Run the live demo")
    print("    convoyield server        Start the Cloud API server")
    print("    convoyield interactive   Chat and see live yield analysis")
    print("    convoyield analyze       Analyze conversation logs")
    print("    convoyield playbooks     Browse premium playbooks")
    print("    convoyield register      Get your API key")
    print("    convoyield status        Check system status")
    print()


def _run_demo():
    """Run the basic usage demo."""
    # Import here to avoid circular imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from examples.basic_usage import main as demo_main
    demo_main()


def _run_server(host: str, port: int):
    """Start the Cloud API server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required to run the server.")
        print("Install it with: pip install 'convoyield[cloud]'")
        sys.exit(1)

    print(f"\n  Starting ConvoYield Cloud Server on {host}:{port}")
    print(f"  Dashboard:  http://localhost:{port}/")
    print(f"  API Docs:   http://localhost:{port}/docs")
    print(f"  Health:     http://localhost:{port}/api/v1/health\n")

    uvicorn.run("cloud.server:app", host=host, port=port, reload=True)


def _run_analyze(file_path: str, base_value: float):
    """Analyze a conversation log file."""
    from convoyield import ConvoYield

    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(path) as f:
        conversations = json.load(f)

    print(f"\n  Analyzing {len(conversations)} conversations...")
    print(f"  Base value: ${base_value:.2f}\n")

    total_yield = 0.0
    total_captured = 0.0
    all_plays = {}
    all_arbitrage = {}

    for i, convo in enumerate(conversations):
        engine = ConvoYield(base_conversation_value=base_value)
        result = engine.process_conversation(convo)

        total_yield += result.estimated_yield
        total_captured += result.yield_captured_so_far

        if result.recommended_play:
            all_plays[result.recommended_play] = all_plays.get(result.recommended_play, 0) + 1

        for arb in result.arbitrage_opportunities:
            all_arbitrage[arb.type] = all_arbitrage.get(arb.type, 0) + 1

        print(f"  [{i+1}/{len(conversations)}] Yield: ${result.estimated_yield:.2f} | "
              f"Play: {result.recommended_play or 'N/A'} | "
              f"Phase: {result.phase}")

    print(f"\n  {'=' * 50}")
    print(f"  Total Estimated Yield:   ${total_yield:.2f}")
    print(f"  Total Captured Yield:    ${total_captured:.2f}")
    print(f"  Value Left on Table:     ${total_yield - total_captured:.2f}")
    print(f"  Avg Yield/Conversation:  ${total_yield / len(conversations):.2f}")

    if all_plays:
        print(f"\n  Top Plays:")
        for play, count in sorted(all_plays.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {play}: {count}x")

    if all_arbitrage:
        print(f"\n  Arbitrage Types:")
        for arb, count in sorted(all_arbitrage.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {arb}: {count}x")

    print()


def _run_register(email: str, server: str):
    """Register for an API key."""
    import urllib.request
    import urllib.error

    url = f"{server}/api/v1/keys"
    data = json.dumps({"email": email, "tier": "free"}).encode()

    try:
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())

        print(f"\n  Registration successful!")
        print(f"  API Key: {result['api_key']}")
        print(f"  Tier:    {result['tier']}")
        print(f"\n  Save this key! You'll need it for your bot integration:")
        print(f"    export CONVOYIELD_API_KEY={result['api_key']}")
        print()

    except urllib.error.URLError:
        print(f"\n  Error: Could not connect to {server}")
        print(f"  Make sure the server is running: convoyield server")
        print()


def _list_playbooks():
    """List available premium playbooks."""
    from convoyield.playbooks import ALL_PLAYBOOKS

    print(f"\n  Premium Playbooks")
    print(f"  {'=' * 50}")

    for pb_id, pb in ALL_PLAYBOOKS.items():
        plays = pb["plays"]
        print(f"\n  {pb['name']}")
        print(f"  {'─' * 40}")
        print(f"  ID:     {pb_id}")
        print(f"  Plays:  {len(plays)}")
        print(f"  Price:  ${pb['price']:.0f}/month")
        print(f"\n  Sample plays:")
        for play in plays[:3]:
            print(f"    - {play['name']}: {play['description'][:60]}...")

    print(f"\n  Total: {sum(len(pb['plays']) for pb in ALL_PLAYBOOKS.values())} plays across {len(ALL_PLAYBOOKS)} playbooks")
    print()


def _check_status(server: str):
    """Check system status."""
    import urllib.request
    import urllib.error

    print(f"\n  ConvoYield System Status")
    print(f"  {'=' * 40}")

    # Check engine
    try:
        from convoyield import ConvoYield
        engine = ConvoYield()
        result = engine.process_user_message("test")
        print(f"  Engine:     OK (v1.0.0)")
    except Exception as e:
        print(f"  Engine:     ERROR ({e})")

    # Check playbooks
    try:
        from convoyield.playbooks import ALL_PLAYBOOKS
        total = sum(len(pb["plays"]) for pb in ALL_PLAYBOOKS.values())
        print(f"  Playbooks:  OK ({total} plays across {len(ALL_PLAYBOOKS)} packs)")
    except Exception as e:
        print(f"  Playbooks:  ERROR ({e})")

    # Check server
    try:
        url = f"{server}/api/v1/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            print(f"  Server:     OK ({result.get('version', 'unknown')})")
    except Exception:
        print(f"  Server:     OFFLINE ({server})")

    print()


def _run_interactive():
    """Interactive conversation mode with live yield analysis."""
    from convoyield import ConvoYield

    engine = ConvoYield(base_conversation_value=50.0)

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  ConvoYield Interactive Mode                     ║")
    print("  ║  Type messages to see live yield analysis.       ║")
    print("  ║  Type 'quit' to exit.                            ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    while True:
        try:
            user_input = input("  YOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        result = engine.process_user_message(user_input)

        print()
        print(f"  ┌─ Yield Analysis {'─' * 40}")
        print(f"  │ Sentiment:     {result.current_sentiment:+.2f} (delta: {result.sentiment_delta:+.2f})")
        print(f"  │ Momentum:      {result.momentum_score:+.2f}")
        print(f"  │ Phase:         {result.phase}")
        print(f"  │ Est. Yield:    ${result.estimated_yield:.2f}")
        print(f"  │ Risk:          {result.risk_level:.0%}")
        print(f"  │ Play:          {result.recommended_play or 'N/A'}")
        print(f"  │ Tone:          {result.recommended_tone}")

        if result.arbitrage_opportunities:
            top = result.top_arbitrage
            print(f"  │")
            print(f"  │ ARBITRAGE: {top.type} (${top.estimated_value:.2f})")

        if result.micro_conversions:
            print(f"  │")
            for mc in result.micro_conversions[:3]:
                print(f"  │ MC: {mc.type} (${mc.value:.2f})")

        if result.recommended_plays:
            print(f"  │")
            top_play = result.recommended_plays[0]
            print(f"  │ Top Play Hints:")
            for hint in top_play.execution_hints[:2]:
                print(f"  │   - {hint}")

        print(f"  └{'─' * 58}")
        print()

        # Record a simulated bot response
        engine.record_bot_response(f"[Bot response to turn {engine.state.turn_count}]")


if __name__ == "__main__":
    main()
