# Multiplayer Stone, Paper, Scissors
A multiplayer Stone, Paper, Scissors game built with Python and WebSockets, playable via the command line across different devices and locations using IPv6.
## How to Run

1. Install Requirements:
   - Ensure you have Python 3.7+ installed.
   - Install the websockets library: `pip install websockets`

2. Start the Server:
   - Run the server on a machine with IPv6 support: `python3 server.py`
   - Note the displayed IPv6 address and port (e.g., ws://[2001:db8::1]:8765).

3. Run Clients:
   - On the same or different devices, open terminals and run: `python3 client.py`
   - Follow the prompts:
     - Enter a username.
     - Input the server’s IPv6 address and port.
     - Choose create to host a room (get a token) or join to connect with a token.

4. Play:
   - Two players can join a room using the same token.
   - Play 3 rounds by entering `R` (Stone), `P` (Paper), or `S` (Scissors).

## Notes
- IPv6 Support: Ensure your network provides global IPv6 addresses for internet play. For local testing, use `::1` (IPv6 localhost).
- Firewall: Allow port `8765` (or your chosen port) in your firewall settings.
- Code: Built with official Python libraries (websockets, asyncio, socket)—no third-party dependencies.

## Example
- Server: ws://[2001:db8::1]:8765
- Client 1: Creates a room, shares token.
- Client 2: Joins with the token, game starts!
