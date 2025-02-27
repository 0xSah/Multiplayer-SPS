import asyncio
import websockets
import json
import uuid

# Store rooms: token -> room state
rooms = {}
# Map WebSocket connections to room tokens
player_rooms = {}

async def notify_players(token, message):
    """Send a message to both players in a room."""
    for player in rooms[token]["players"]:
        await player.send(json.dumps(message))

def determine_winner(choices):
    """Determine the winner of a round: R (Stone), P (Paper), S (Scissors)."""
    if choices[0] == choices[1]:
        return "tie"
    choices_list = ["R", "P", "S"]
    index1 = choices_list.index(choices[0])
    index2 = choices_list.index(choices[1])
    return 0 if (index1 - index2) % 3 == 1 else 1  # 0: Player 1 wins, 1: Player 2 wins

async def run_game(token):
    """Run a 3-round game for a room."""
    room = rooms[token]
    for round_num in range(1, 4):
        room["round"] = round_num
        room["choices"] = [None, None]
        usernames = room["player_usernames"]
        await notify_players(token, {
            "status": "round_start",
            "round": round_num,
            "message": f"Round {round_num}: Enter your choice (R for Stone, P for Paper, S for Scissors)"
        })
        while None in room["choices"]:
            await asyncio.sleep(0.1)
        winner = determine_winner(room["choices"])
        if winner != "tie":
            room["scores"][winner] += 1
        winner_name = "Tie" if winner == "tie" else usernames[winner]
        await notify_players(token, {
            "status": "round_result",
            "round": round_num,
            "winner": winner_name,
            "scores": room["scores"],
            "choices": room["choices"]
        })
    # Determine overall winner
    scores = room["scores"]
    usernames = room["player_usernames"]
    overall_winner = usernames[0] if scores[0] > scores[1] else usernames[1] if scores[1] > scores[0] else "Tie"
    await notify_players(token, {
        "status": "game_over",
        "winner": overall_winner,
        "final_scores": scores
    })
    # Clean up
    del rooms[token]
    for ws in room["players"]:
        if ws in player_rooms:
            del player_rooms[ws]

async def handle_client(websocket, path):
    """Handle incoming client messages."""
    player_rooms[websocket] = None
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "create_room":
                if len(rooms) >= 50:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Server is full"
                    }))
                    continue
                token = str(uuid.uuid4())
                rooms[token] = {
                    "players": [websocket],
                    "choices": [None, None],
                    "scores": [0, 0],
                    "round": 0,
                    "player_usernames": [data.get("username")]
                }
                player_rooms[websocket] = token
                print(f"Room created: {token} by {data.get('username')}")
                await websocket.send(json.dumps({
                    "status": "room_created",
                    "token": token,
                    "message": f"Room created. Share this token: {token}"
                }))
                await websocket.send(json.dumps({
                    "status": "waiting_for_opponent",
                    "message": "Waiting for another player to join..."
                }))

            elif action == "join_room":
                token = data.get("token")
                if not isinstance(token, str) or token not in rooms:
                    print(f"Join failed: Invalid token {token} from {data.get('username')}")
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Room does not exist or invalid token"
                    }))
                    continue
                if len(rooms[token]["players"]) >= 2:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Room is full"
                    }))
                    continue
                rooms[token]["players"].append(websocket)
                rooms[token]["player_usernames"].append(data.get("username"))
                player_rooms[websocket] = token
                usernames = rooms[token]["player_usernames"]
                print(f"{data.get('username')} joined room {token}")
                await notify_players(token, {
                    "status": "game_start",
                    "opponents": usernames,
                    "message": f"Game starting! {usernames[0]} vs {usernames[1]}"
                })
                asyncio.create_task(run_game(token))

            elif action == "play":
                token = player_rooms.get(websocket)
                if token and rooms[token]["round"] > 0:
                    player_index = rooms[token]["players"].index(websocket)
                    choice = data.get("choice").upper()
                    if choice in ["R", "P", "S"] and rooms[token]["choices"][player_index] is None:
                        rooms[token]["choices"][player_index] = choice
                    else:
                        await websocket.send(json.dumps({
                            "status": "error",
                            "message": "Invalid choice or already submitted"
                        }))

    except websockets.ConnectionClosed:
        token = player_rooms.get(websocket)
        if token and token in rooms:
            remaining_players = [p for p in rooms[token]["players"] if p != websocket]
            if remaining_players:
                await remaining_players[0].send(json.dumps({
                    "status": "error",
                    "message": "Opponent disconnected. Game over."
                }))
            print(f"Player disconnected from room {token}")
            del rooms[token]
            for ws in rooms[token]["players"]:
                if ws in player_rooms:
                    del player_rooms[ws]
        if websocket in player_rooms:
            del player_rooms[websocket]

# Start the server
start_server = websockets.serve(handle_client, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
print("Server running on ws://localhost:8765")
asyncio.get_event_loop().run_forever()