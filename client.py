import asyncio
import websockets
import threading
import queue
import json

# Queue for user inputs from the separate thread
input_queue = queue.Queue()
# Map choices to readable names
choice_map = {"R": "Stone", "P": "Paper", "S": "Scissors"}
# Track game state
game_state = "initial"  # initial, waiting, playing, ended
waiting_for_choice = False

def input_thread():
    """Collect user input in a separate thread and add to the queue."""
    while True:
        user_input = input()
        input_queue.put(user_input.strip())

async def client():
    """Main client logic for connecting to the server and playing the game."""
    global game_state, waiting_for_choice

    print("Welcome to Stone, Paper, Scissors!")
    # Clear any stray inputs before the first prompt
    while not input_queue.empty():
        input_queue.get_nowait()
    username = input("Enter your username: ").strip()

    # Clear queue again before the next prompt
    while not input_queue.empty():
        input_queue.get_nowait()
    choice = input("Type 'create' to create a room or 'join' to join a room: ").lower()

    # Start the input thread only after all initial synchronous prompts
    input_thread_instance = threading.Thread(target=input_thread, daemon=True)
    input_thread_instance.start()

    async with websockets.connect("ws://localhost:8765") as websocket:
        if choice == "create":
            await websocket.send(json.dumps({
                "action": "create_room",
                "username": username
            }))
            game_state = "waiting"
        elif choice == "join":
            # Clear queue before token prompt
            while not input_queue.empty():
                input_queue.get_nowait()
            token = input("Enter the room token: ").strip()
            await websocket.send(json.dumps({
                "action": "join_room",
                "username": username,
                "token": token
            }))
            game_state = "waiting"
        else:
            print("Invalid option. Exiting.")
            return

        opponents = None
        while game_state != "ended":
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                data = json.loads(message)
                status = data.get("status")

                if status == "room_created":
                    print(data["message"])

                elif status == "waiting_for_opponent":
                    print(data["message"])
                    game_state = "waiting"

                elif status == "game_start":
                    opponents = data["opponents"]
                    opponent = [u for u in opponents if u != username][0]
                    print(data["message"])
                    print(f"Playing against: {opponent}")
                    game_state = "playing"

                elif status == "round_start" and game_state == "playing":
                    print(data["message"])
                    waiting_for_choice = True
                    while waiting_for_choice:
                        try:
                            user_input = input_queue.get_nowait().upper()
                            if user_input in ["R", "P", "S"]:
                                await websocket.send(json.dumps({
                                    "action": "play",
                                    "choice": user_input
                                }))
                                waiting_for_choice = False
                            elif user_input == "EXIT":
                                print("Exiting game.")
                                game_state = "ended"
                                return
                            elif user_input != "":
                                print("Invalid choice. Use R, P, or S.")
                        except queue.Empty:
                            await asyncio.sleep(0.1)

                elif status == "round_result":
                    your_choice = choice_map[data["choices"][0 if opponents[0] == username else 1]]
                    opponent_choice = choice_map[data["choices"][1 if opponents[0] == username else 0]]
                    if data["winner"] == "Tie":
                        print(f"Round {data['round']} result: It's a tie!")
                    else:
                        print(f"Round {data['round']} result: {data['winner']} wins!")
                    print(f"Choices: You: {your_choice}, Opponent: {opponent_choice}")
                    print(f"Scores: {data['scores']}")

                elif status == "game_over":
                    print(f"Game Over! Winner: {data['winner']}")
                    print(f"Final Scores: {data['final_scores']}")
                    game_state = "ended"

                elif status == "error":
                    print(f"Error: {data['message']}")
                    if "disconnected" in data["message"] or "Server is full" in data["message"]:
                        game_state = "ended"

            except asyncio.TimeoutError:
                if not waiting_for_choice:
                    while not input_queue.empty():
                        input_queue.get_nowait()  # Clear stray inputs outside rounds

# Run the client
asyncio.run(client())