from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import database
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all (OK for dev)
    allow_credentials=True,
    allow_methods=["*"],   # allow OPTIONS, POST, GET
    allow_headers=["*"],
)
# ---------------- HEALTH CHECK ----------------
@app.get("/")
def health_check():
    return {"status": "Server is running"}


# ---------------- SAFE SESSION ID EXTRACTOR ----------------
def get_session_id(output_contexts: list):
    for ctx in output_contexts:
        name = ctx.get("name", "")
        if "/sessions/" in name:
            return name.split("/sessions/")[1].split("/")[0]
    return None


# ---------------- IN-MEMORY STORAGE ----------------
session_orders = {}       
session_order_ids = {}     

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()

    query_result = payload.get("queryResult", {})
    intent = query_result.get("intent", {}).get("displayName", "")
    parameters = query_result.get("parameters", {})
    output_contexts = query_result.get("outputContexts", [])

    session_id = get_session_id(output_contexts)
    if not session_id:
        session_id = "fallback-session"

    if intent == "track.order":
        return track_order(parameters)

    elif intent == "order.add":
        return add_order(session_id, parameters)

    elif intent == "order.remove":
        return remove_order(
            session_id,
            parameters,
            session_order_ids.get(session_id)
        )

    elif intent == "order.complete":
        return complete_order(parameters, session_id)

    return JSONResponse(
        content={"fulfillmentText": "Please tell me what you'd like to order 🙂"}
    )


# ---------------- TRACK ORDER ----------------
def track_order(parameters: dict):
    try:
        order_id = int(parameters.get("order_id"))
    except:
        return JSONResponse(
            content={"fulfillmentText": "Please provide a valid order ID."}
        )

    status = database.get_status(order_id)
    if status:
        return JSONResponse(
            content={"fulfillmentText": f"Your order status for ID {order_id} is {status}."}
        )
    else:
        return JSONResponse(
            content={"fulfillmentText": f"No order found with ID {order_id}."}
        )


# ---------------- ADD ORDER ----------------
def add_order(session_id: str, parameters: dict):
    food_items = parameters.get("food_items", [])
    numbers = parameters.get("number", [])

    if not isinstance(food_items, list):
        food_items = [food_items]
    if not isinstance(numbers, list):
        numbers = [numbers]

    if len(food_items) != len(numbers):
        return JSONResponse(
            content={"fulfillmentText": "Please mention quantity for all food items."}
        )

    if session_id not in session_order_ids:
        session_order_ids[session_id] = database.get_next_order_id()

    if session_id not in session_orders:
        session_orders[session_id] = {}

    for i in range(len(food_items)):
        item = food_items[i]
        qty = int(numbers[i])

        if item in session_orders[session_id]:
            session_orders[session_id][item] += qty
        else:
            session_orders[session_id][item] = qty

    summary = [
        f"{qty} {item}" for item, qty in session_orders[session_id].items()
    ]

    return JSONResponse(
        content={
            "fulfillmentText": (
                f"Till now, your order has {', '.join(summary)}. "
                f"Do you want to add anything else?"
            )
        }
    )


# ---------------- REMOVE ORDER ----------------
def remove_order(session_id: str, parameters: dict, order_id: int = None):
    food_items = parameters.get("food_items", [])
    numbers = parameters.get("number", [])

    if not isinstance(food_items, list):
        food_items = [food_items]
    if not isinstance(numbers, list):
        numbers = [numbers]

    removed_items = []
    not_found_items = []

    # ---------- BEFORE COMPLETION (SESSION) ----------
    if session_id in session_orders and session_orders[session_id]:
        for i in range(len(food_items)):
            item = food_items[i]
            qty = int(numbers[i])

            if item not in session_orders[session_id]:
                not_found_items.append(item)
                continue

            if session_orders[session_id][item] > qty:
                session_orders[session_id][item] -= qty
                removed_items.append(f"{qty} {item}")
            else:
                removed_items.append(f"{session_orders[session_id][item]} {item}")
                del session_orders[session_id][item]

    # ---------- AFTER COMPLETION (DATABASE) ----------
    if order_id is not None:
        for i in range(len(food_items)):
            database.remove_order_items(
                order_id,
                food_items[i],
                int(numbers[i])
            )

    response = []
    if removed_items:
        response.append(f"I've removed {', '.join(removed_items)} from your order.")
    if not_found_items:
        response.append(f"{', '.join(not_found_items)} was not in your order.")

    if session_id in session_orders and session_orders[session_id]:
        remaining = [
            f"{qty} {item}" for item, qty in session_orders[session_id].items()
        ]
        response.append(f"Now you have {', '.join(remaining)}.")
    else:
        response.append("Your order is now empty.")

    return JSONResponse(
        content={"fulfillmentText": " ".join(response)}
    )


# ---------------- COMPLETE ORDER ----------------
def complete_order(parameters: dict, session_id: str):
    if session_id not in session_orders or not session_orders[session_id]:
        return JSONResponse(
            content={"fulfillmentText": "Your order is empty. Please add items first."}
        )

    order_id = session_order_ids.get(session_id)
    order = session_orders[session_id]

    # Save to DB using SAME order_id
    for food_item, quantity in order.items():
        database.insert_order(order_id, food_item, quantity)

    database.insert_order_status(order_id, "In Progress")

    total_price = database.total_order_price(order_id)

    # Clear only session order (NOT order_id)
    del session_orders[session_id]

    return JSONResponse(
        content={
            "fulfillmentText": (
                f"Your order has been placed successfully! "
                f"Your order ID is {order_id}. "
                f"The total amount is ₹{total_price}, payable at delivery."
            )
        }
    )
