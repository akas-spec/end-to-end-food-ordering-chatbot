import psycopg2

global conn
conn = psycopg2.connect(
    host="localhost",
    database="ijju_eatery",
    user="postgres",
    password="akash@230105",
    port=5432
)

# ---------------- GET ORDER STATUS ----------------
def get_status(order_id: int):
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM order_tracking WHERE order_id = %s",
            (order_id,)
        )
        result = cur.fetchone()
        cur.close()

        return result[0] if result else None

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        return None


# ---------------- GET NEXT ORDER ID ----------------
def get_next_order_id():
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(order_id), 0) + 1 FROM orders;")
        next_id = cur.fetchone()[0]
        cur.close()
        return next_id

    except Exception as e:
        conn.rollback()
        print("Error getting next order_id:", e)
        return None


# ---------------- INSERT ORDER ITEM ----------------
def insert_order(order_id: int, food_item: str, quantity: int):
    try:
        cur = conn.cursor()

        # get food_item_id
        cur.execute(
            "SELECT id FROM food_items WHERE LOWER(food_item) = LOWER(%s)",
            (food_item,)
        )
        row = cur.fetchone()

        if row is None:
            cur.close()
            print("Invalid food item:", food_item)
            return False

        food_item_id = row[0]

        # insert order
        cur.execute(
            """
            INSERT INTO orders (order_id, food_item_id, quantity)
            VALUES (%s, %s, %s)
            """,
            (order_id, food_item_id, quantity)
        )

        conn.commit()
        cur.close()
        return True

    except Exception as e:
        conn.rollback()  
        print("DB ERROR:", e)
        return False



# ---------------- TOTAL ORDER PRICE (FIXED) ----------------
def total_order_price(order_id: int):
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COALESCE(SUM(o.quantity * f.price), 0)
            FROM orders o
            JOIN food_items f
              ON o.food_item_id = f.id
            WHERE o.order_id = %s
            """,
            (order_id,)
        )

        total_price = cur.fetchone()[0]
        cur.close()
        return total_price

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        return 0

# ---------------- INSERT ORDER STATUS ----------------
def insert_order_status(order_id: int, status: str):
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO order_tracking (order_id, status)
            VALUES (%s, %s)
            """,
            (order_id, status)
        )
        conn.commit()
        cur.close()
        return True

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        return False
def remove_order_items(order_id: int, food_item: str, quantity: int):
    try:
        cur = conn.cursor()

        # get food_item_id
        cur.execute(
            "SELECT id FROM food_items WHERE LOWER(food_item) = LOWER(%s)",
            (food_item,)
        )
        row = cur.fetchone()

        if row is None:
            cur.close()
            return False

        food_item_id = row[0]

        # get current quantity
        cur.execute(
            """
            SELECT quantity
            FROM orders
            WHERE order_id = %s AND food_item_id = %s
            """,
            (order_id, food_item_id)
        )
        result = cur.fetchone()

        if result is None:
            cur.close()
            return False

        current_qty = result[0]

        if current_qty > quantity:
            # reduce quantity
            cur.execute(
                """
                UPDATE orders
                SET quantity = quantity - %s
                WHERE order_id = %s AND food_item_id = %s
                """,
                (quantity, order_id, food_item_id)
            )
        else:
            # delete item
            cur.execute(
                """
                DELETE FROM orders
                WHERE order_id = %s AND food_item_id = %s
                """,
                (order_id, food_item_id)
            )

        conn.commit()
        cur.close()
        return True

    except Exception as e:
        conn.rollback()
        print("DB ERROR:", e)
        return False
