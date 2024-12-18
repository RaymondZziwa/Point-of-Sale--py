import tkinter as tk
import sqlite3
import os
from tkinter import PhotoImage
from tkinter import ttk, messagebox, simpledialog, filedialog
import barcode
from barcode.writer import ImageWriter
from tkinter.simpledialog import askstring
import csv
import win32print
import win32api
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from reportlab.lib.pagesizes import inch
# import win32print
# import win32ui
# from win32con import SRCCOPY

# Function to initialize or connect to the database
def initialize_database():
    # Ensure the directory for the database exists
    db_dir = 'db'
    db_path = os.path.join(db_dir, 'pos.db')

    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Check if the database file already exists
    if not os.path.exists(db_path):
        print("Database not found. Creating a new one...")
    else:
        print("Database already exists. Connecting to the existing database.")

    # Connect to the database (will create the file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the items table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            barcode TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create the store table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
        )
    ''')
    
    # Create the store table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            notes TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
        )
    ''')
    
    # Create the sales_records table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            discount FLOAT NOT NULL,
            total FLOAT NOT NULL,
            payment_method TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

# Function to connect to the existing database
def connect_database():
    try:
        initialize_database()
        db_path = os.path.join('db', 'pos.db')
        conn = sqlite3.connect(db_path)  # Connect to the existing database
        print('db connection is successful')
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Function to generate EAN-13 barcode
def generate_barcode(item_name):
    ean = barcode.get_barcode_class('ean13')
    # Generate a unique 12-digit number (EAN-13 appends a checksum digit)
    base_number = str(len(items_data) + 1).zfill(12)
    barcode_image = ean(base_number, writer=ImageWriter())
    
    # Save the barcode image
    barcode_dir = "barcodes"
    os.makedirs(barcode_dir, exist_ok=True)
    file_path = os.path.join(barcode_dir, f"{item_name}.png")
    barcode_image.save(file_path)
    return base_number, file_path

def show_items():
    """Display the items list and functionality in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Add Item Button
    add_button = tk.Button(content_frame, text="Add Item", command=add_item)
    add_button.pack(pady=10, anchor="w")

    # Treeview for displaying items
    columns = ("ID", "Name", "Price", "Actions")
    items_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    items_table.heading("ID", text="ID")
    items_table.heading("Name", text="Name")
    items_table.heading("Price", text="Price")
    items_table.heading("Actions", text="Actions")
    items_table.column("Actions", width=200)
    items_table.pack(fill="both", expand=1, padx=10, pady=10)

    # Query items from the database
    try:
        conn = connect_database()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM items")
        items = cursor.fetchall()  # Fetch all rows from the query result
        conn.close()

        # Populate the table
        for item in items:
            # `item` is a tuple (id, name, price)
            action_text = "Delete | Update"
            items_table.insert("", "end", values=(item[0], item[1], item[2], action_text))
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch items: {e}")

    # Event handler for clickable actions
    def handle_click(event):
        item = items_table.identify_row(event.y)  # Get the clicked row
        column = items_table.identify_column(event.x)  # Get the clicked column

        if item and column == "#4":  # Check if the "Actions" column is clicked
            selected_item = items_table.item(item, "values")
            item_id = selected_item[0]  # The item ID
            x_position = event.x - items_table.bbox(item, column="#4")[0]  # X position within the Actions cell

            # Split actions into clickable zones
            if x_position < 50:  # Assume "Delete" is in the left part
                delete_item(item_id)
            else:  # Assume "Update" is in the right part
                update_item_popup(item_id, selected_item[1], selected_item[2])

    items_table.bind("<Button-1>", handle_click)  # Bind left-click event

# Function to delete an item
def delete_item(item_id):
    """Delete an item by its ID."""
    if messagebox.askyesno("Delete Item", f"Are you sure you want to delete item ID {item_id}?"):
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            show_items()  # Refresh the items list
            messagebox.showinfo("Success", f"Item ID {item_id} deleted successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete item: {e}")

# Function to update an item
def update_item_popup(item_id, name, price):
    """Open a popup to update the item details."""
    update_popup = tk.Toplevel()
    update_popup.title("Update Item")
    update_popup.geometry("300x200")

    # Name label and entry
    tk.Label(update_popup, text="Name:").pack(pady=5)
    name_entry = tk.Entry(update_popup)
    name_entry.insert(0, name)
    name_entry.pack(pady=5)

    # Price label and entry
    tk.Label(update_popup, text="Price:").pack(pady=5)
    price_entry = tk.Entry(update_popup)
    price_entry.insert(0, price)
    price_entry.pack(pady=5)

    # Confirm button
    def confirm_update():
        new_name = name_entry.get()
        new_price = price_entry.get()
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET name = ?, price = ? WHERE id = ?", (new_name, new_price, item_id))
            conn.commit()
            conn.close()
            update_popup.destroy()
            show_items()  # Refresh the items list
            messagebox.showinfo("Success", f"Item ID {item_id} updated successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update item: {e}")

    tk.Button(update_popup, text="Confirm", command=confirm_update).pack(pady=10)

def stock_taking():
    """Display store stock taking list and functionality in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Treeview for displaying items
    columns = ("ID", "Name", "Quantity")
    items_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    items_table.heading("ID", text="ID")
    items_table.heading("Name", text="Name")
    items_table.heading("Quantity", text="Quantity")

    # Query items from the database
    try:
        conn = connect_database()
        cursor = conn.cursor()
        # Update the SELECT query to include the item's name
        cursor.execute("""
            SELECT 
                store.id, 
                store.item_id,
                items.name, 
                store.quantity 
                    FROM 
                        store 
                    JOIN 
                        items 
                    ON
                        items.id = store.item_id
                """)
        items = cursor.fetchall()  # Fetch all rows from the query result
        conn.close()

            # Populate the table
        for item in items:
            # Insert the item's name instead of its id
            items_table.insert("", "end", values=(item[0], item[2], item[3]))
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch items: {e}")

    items_table.pack(fill="both", expand=1, padx=10, pady=10)


def sales_records():
    """Display sales records list and functionality in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Configure content frame background
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Sales Records", font=("Helvetica", 16), bg="white").pack(pady=10)

    # Treeview for displaying sales records
    columns = ("ID", "Product", "Client Name", "Client Phone", "Quantity", "Discount", "Total", "Payment Method", "Date")
    sales_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    sales_table.pack(fill="both", expand=1, padx=10, pady=10)

    # Define column headings
    for col in columns:
        sales_table.heading(col, text=col)
        sales_table.column(col, anchor="center", width=120)

    # Query sales data from the database
    try:
        conn = connect_database()
        cursor = conn.cursor()
        # Select relevant fields from the sales table
        cursor.execute("""
            SELECT 
                s.id, 
                i.name AS product_name, 
                s.client_name, 
                s.client_phone, 
                s.quantity, 
                s.discount, 
                s.total, 
                s.payment_method, 
                s.createdAt
            FROM 
                sales s 
            JOIN 
                items i 
            ON 
                s.product_id = i.id
            ORDER BY 
                s.createdAt DESC
        """)
        sales = cursor.fetchall()  # Fetch all rows from the query result
        conn.close()

        # Populate the table with sales data
        for sale in sales:
            sales_table.insert("", "end", values=sale)
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch sales records: {e}")

    # Add scrollbar
    scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=sales_table.yview)
    sales_table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Add export to CSV button
    def export_to_csv():
        """Export sales records to a CSV file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV files", "*.csv")], 
            title="Save as"
        )
        if not file_path:
            return  # User canceled the save dialog

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                # Write headers
                writer.writerow(columns)
                # Write data
                for row in sales_table.get_children():
                    writer.writerow(sales_table.item (row)["values"])
            messagebox.showinfo("Export Success", f"Sales records exported successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export sales records: {e}")

    tk.Button(content_frame, text="Export to CSV", command=export_to_csv).pack(pady=10)


def add_action_buttons(items_table, row_id):
    """Add Update/Delete buttons to a Treeview row."""
    actions_frame = ttk.Frame(items_table)
    
    # Update Button
    update_button = ttk.Button(actions_frame, text="Update", command=lambda: update_item(row_id))
    update_button.pack(side="left", padx=5)

    # Delete Button
    delete_button = ttk.Button(actions_frame, text="Delete", command=lambda: delete_item(row_id))
    delete_button.pack(side="left", padx=5)

    # Attach the frame to the "Actions" column in the Treeview
    items_table.item(row_id, values=(*items_table.item(row_id, "values")[:-1], actions_frame))


def add_item():
    """Add a new item with a modal."""
    add_item_modal = tk.Toplevel(root)
    add_item_modal.title("Add New Item")

    # Item Name
    tk.Label(add_item_modal, text="Item Name:").grid(row=0, column=0, padx=10, pady=5)
    name_entry = tk.Entry(add_item_modal)
    name_entry.grid(row=0, column=1, padx=10, pady=5)

    # Item Price
    tk.Label(add_item_modal, text="Item Price:").grid(row=1, column=0, padx=10, pady=5)
    price_entry = tk.Entry(add_item_modal)
    price_entry.grid(row=1, column=1, padx=10, pady=5)

    def confirm_add_item():
        name = name_entry.get().strip()
        price = price_entry.get().strip()

        if not name or not price:
            messagebox.showerror("Error", "All fields are required!")
            return

        try:
            price = float(price)
        except ValueError:
            messagebox.showerror("Error", "Price must be a valid number!")
            return

        # Generate a barcode
        barcode_number = f"{len(name) * 100000000000:013d}"  # Example EAN-13
        barcode_cls = barcode.get_barcode_class("ean13")
        ean = barcode_cls(barcode_number)
        barcode_path = os.path.join("barcodes", f"{name}.png")

        # Ensure the barcode directory exists
        os.makedirs("barcodes", exist_ok=True)

        ean.save(barcode_path)

        # Add to SQLite database
        try:
            conn = connect_database()
            cursor = conn.cursor()

            # Insert into items table
            cursor.execute('''
                INSERT INTO items (name, price, barcode) 
                VALUES (?, ?, ?)
            ''', (name, f"{price:.2f}", barcode_number))

            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Item '{name}' added successfully!")
            add_item_modal.destroy()

            # Optionally, refresh the item list in the GUI
            show_items()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add item: {e}")
            add_item_modal.destroy()

    # Confirm Button
    confirm_button = tk.Button(add_item_modal, text="Confirm", command=confirm_add_item)
    confirm_button.grid(row=2, column=0, columnspan=2, pady=10)

    add_item_modal.transient(root)
    add_item_modal.grab_set()
    add_item_modal.wait_window()


#pos
def show_pos():
    """Display the POS interface."""
    clear_content_frame()  # Clear previous content in the content frame
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Point of Sale", font=("Helvetica", 16), bg='white').pack(pady=10)

    # Searchable Dropdown for products
    search_frame = tk.Frame(content_frame, bg="white")
    search_frame.pack(pady=10, fill="x", padx=10)

    tk.Label(search_frame, text="Search Product:", bg="white").pack(side="left", padx=5)

    product_search_var = tk.StringVar()
    product_search_combobox = ttk.Combobox(search_frame, textvariable=product_search_var, width=30)
    product_search_combobox.pack(side="left", padx=5)

    # Load product data for the dropdown
    try:
        conn = connect_database()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM items")
        products = cursor.fetchall()
        conn.close()
        product_search_combobox["values"] = [f"{product[1]} - {product[2]}" for product in products]
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch products: {e}")
        return

    # Cart Table
    columns = ("ID", "Name", "Price", "Quantity", "Discount", "Total")
    cart_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    for col in columns:
        cart_table.heading(col, text=col)
        cart_table.column(col, width=120, anchor="center")
    cart_table.pack(pady=10, fill="both", expand=1)

    # Add product to cart
    def add_to_cart(event=None):  # Optional event parameter for key binding
        selected_product = product_search_combobox.get()
        if not selected_product:
            messagebox.showerror("Error", "Please select a product!")
            return

        product_name, price = selected_product.rsplit(" - ", 1)
        product_id = next((product[0] for product in products if product[1] == product_name), None)
        price = float(price)

        # Add the product to the cart or update existing quantity
        for child in cart_table.get_children():
            item = cart_table.item(child, "values")
            if item[1] == product_name:
                quantity = int(item[3]) + 1
                total = (quantity * price) - float(item[4])
                cart_table.item(child, values=(product_id, product_name, price, quantity, item[4], total))
                return

        # New item in the cart
        cart_table.insert("", "end", values=(product_id, product_name, price, 1, 0, price))

    # Bind Enter key to add_to_cart function
    product_search_combobox.bind("<Return>", add_to_cart)

    tk.Button(search_frame, text="Add to Cart", command=add_to_cart).pack(side="left", padx=5)

    # Update cart quantities and discounts
    def update_cart(action, item_id):
        for child in cart_table.get_children():
            item = cart_table.item(child, "values")
            if item[0] == item_id:
                price = float(item[2])
                quantity = int(item[3])
                discount = float(item[4])

                if action == "increase":
                    quantity += 1
                elif action == "decrease" and quantity > 1:
                    quantity -= 1
                elif action == "discount":
                    discount_input = askstring("Discount", "Enter Discount Amount:")
                    try:
                        discount = float(discount_input) if discount_input else 0
                    except ValueError:
                        messagebox.showerror("Invalid Discount", "Please enter a valid number.")
                        return

                total = (quantity * price) - discount
                cart_table.item(child, values=(item[0], item[1], price, quantity, discount, total))
                return

    # Controls for modifying cart items
    def modify_cart(action):
        selected_item = cart_table.selection()
        if not selected_item:
            messagebox.showerror("Error", "No item selected!")
            return
        item_id = cart_table.item(selected_item[0], "values")[0]
        update_cart(action, item_id)

    # Buttons for cart operations
    button_frame = tk.Frame(content_frame, bg="white")
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Increase Quantity", command=lambda: modify_cart("increase"), bg="blue", fg="white").pack(side="left", padx=5)
    tk.Button(button_frame, text="Decrease Quantity", command=lambda: modify_cart("decrease"), bg="orange", fg="white").pack(side="left", padx=5)
    tk.Button(button_frame, text="Apply Discount", command=lambda: modify_cart("discount"), bg="green", fg="white").pack(side="left", padx=5)

    # Checkout functionality
    def checkout():
        if not cart_table.get_children():
            messagebox.showerror("Error", "Cart is empty!")
            return

        # Collect client details
        client_name = askstring("Client Details", "Enter Client Name:")
        client_phone = askstring("Client Details", "Enter Client Phone:")
        payment_method = askstring("Payment Method", "Enter Payment Method:")
        
        if not client_name or not client_phone:
            messagebox.showerror("Error", "Client details are required!")
            return

        # Generate receipt and save to database
        receipt = (
            f"Receipt\n"
            f"Client: {client_name}\n"
            f"Phone: {client_phone}\n"
            f"Payment method: {payment_method}\n\n"
            f"{'Item':<20}{'Qty':<10}{'Price':<10}{'Total':<10}\n"
            f"{'-'*60}\n"
        )
        total_amount = 0

        try:
            conn = connect_database()
            cursor = conn.cursor()

            for child in cart_table.get_children():
                item = cart_table.item(child, "values")
                print(item)
                product_id, name, price, quantity, discount, total = item
                total_amount += float(total)
                existing_record = cursor.execute('SELECT quantity FROM store WHERE item_id = ?', (product_id)).fetchone()
                if existing_record:
                    stock_quantity = existing_record[0]
                    if stock_quantity <= 0:
                        messagebox.showerror("Input Error", f"Product {name} is out of stock.")
                        return
                    elif int(stock_quantity) < int(quantity):  # If there is not enough quantity to reduce
                        messagebox.showerror("Input Error", f"Insufficient stock for {name}.")
                        return   
                    else:
                        cursor.execute('UPDATE store SET quantity = ? WHERE item_id = ?', (int(stock_quantity) - int(quantity), product_id))                 
                else:
                    messagebox.showerror("Stock Error", f"Insufficient stock for {name}.")
                    return
                # Save sale to database (example schema)
                cursor.execute(
                    "INSERT INTO sales (product_id, client_name, client_phone, quantity, discount, total, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (product_id, client_name, client_phone, quantity, discount, total, payment_method),
                )

                # Add item to receipt
                receipt += f"{name:<20}{quantity:<10}{price:<10}{total:<10}\n"

            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save sale: {e}")
            return

        receipt += f"\nTotal: {total_amount}\nThank you for your purchase!"
        
        # Print the receipt
        format_receipt(receipt, client_name)
        
        # Display receipt in a new window
        receipt_window = tk.Toplevel()
        receipt_window.title("Receipt")
        receipt_window.geometry("600x600")
        text_widget = tk.Text(receipt_window, wrap="word", height=20, width=50)
        text_widget.insert("1.0", receipt)
        text_widget.pack()
        cart_table.delete(*cart_table.get_children())  # Clear cart after checkout

    # Checkout Button
    tk.Button(content_frame, text="Checkout", command=checkout, bg="green", fg="white").pack(pady=10)


# Function to print receipt
def format_receipt(receipt_text, client_name):
    now = datetime.now()

    # Format date and time as a string
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    # Generate the PDF file
    receipt_filename = f"{client_name}_{timestamp}.pdf"
    create_pdf(receipt_text, receipt_filename)

# Function to generate a PDF using reportlab
def create_pdf(receipt_text, filename):
    """Create a PDF receipt with custom size and save it in a 'receipts' folder."""
    
    # Define the receipt paper size: 3 inches wide x 11 inches high
    receipt_width = 3 * inch
    receipt_height = 11 * inch
    receipt_size = (receipt_width, receipt_height)

    # Ensure the 'receipts' folder exists
    receipts_folder = "receipts"
    os.makedirs(receipts_folder, exist_ok=True)

    # Generate the full path for the PDF file
    full_path = os.path.join(receipts_folder, filename)

    # Create the canvas with custom page size
    c = canvas.Canvas(full_path, pagesize=receipt_size)

    # Add receipt content
    margin_x = 20  # Left margin
    margin_y = receipt_height - 30  # Top margin
    text_object = c.beginText(margin_x, margin_y)
    text_object.setFont("Helvetica", 10)

    # Add each line of the receipt text
    for line in receipt_text.split("\n"):
        text_object.textLine(line)
    
    # Draw the text and save the PDF
    c.drawText(text_object)
    c.save()

    print_receipt(full_path)

# Function to send PDF to the printer using win32print
def print_receipt(filepath):
    print(filepath)
    printer_name = win32print.GetDefaultPrinter()
    print(f"Sending to printer: {printer_name}")
    
    # Use win32api to print the file
    win32api.ShellExecute(
        0, 
        "print", 
        filepath, 
        None, 
        ".", 
        0
    )

def monthly_sales_analysis():
    """Display monthly sales analysis in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Configure content frame background
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Monthly Sales Analysis", font=("Helvetica", 16), bg="white").pack(pady=10)

    # Year filter
    tk.Label(content_frame, text="Filter by Year:", bg="white").pack(pady=5)
    year_entry = tk.Entry(content_frame)
    year_entry.pack(pady=5)

    def fetch_monthly_sales():
        year = year_entry.get()
        if not year.isdigit():
            messagebox.showerror("Input Error", "Please enter a valid year.")
            return

        # Treeview for displaying monthly sales
        columns = ("Month", "Total Income")
        monthly_sales_table = ttk.Treeview(content_frame, columns=columns, show="headings")
        monthly_sales_table.pack(fill="both", expand=1, padx=10, pady=10)

        # Define column headings
        for col in columns:
            monthly_sales_table.heading(col, text=col)
            monthly_sales_table.column(col, anchor="center", width=200)

        # Query monthly sales data from the database
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    STRFTIME('%Y-%m', createdAt) AS sale_month, 
                    SUM(total) AS total_income
                FROM 
                    sales
                WHERE
                    STRFTIME('%Y', createdAt) = ?
                GROUP BY 
                    sale_month
                ORDER BY 
                    sale_month DESC
            """, (year,))
            monthly_sales = cursor.fetchall()  # Fetch all rows from the query result
            conn.close()

            # Populate the table with monthly sales data
            for sale in monthly_sales:
                monthly_sales_table.insert("", "end", values=sale)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch monthly sales analysis: {e}")

    tk.Button(content_frame, text="Fetch Monthly Sales", command=fetch_monthly_sales).pack(pady=10)


def weekly_sales_analysis():
    """Display weekly sales analysis in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Configure content frame background
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Weekly Sales Analysis", font=("Helvetica", 16), bg="white").pack(pady=10)

    # Year filter
    tk.Label(content_frame, text="Filter by Year:", bg="white").pack(pady=5)
    year_entry = tk.Entry(content_frame)
    year_entry.pack(pady=5)

    def fetch_weekly_sales():
        year = year_entry.get()
        if not year.isdigit():
            messagebox.showerror("Input Error", "Please enter a valid year.")
            return

        # Treeview for displaying weekly sales
        columns = ("Week", "Total Income")
        weekly_sales_table = ttk.Treeview(content_frame, columns=columns, show="headings")
        weekly_sales_table.pack(fill="both", expand=1, padx=10, pady=10)

        # Define column headings
        for col in columns:
            weekly_sales_table.heading(col, text=col)
            weekly_sales_table.column(col, anchor="center", width=200)

        # Query weekly sales data from the database
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    STRFTIME('%Y-%m', createdAt) || '-W' || (CAST(STRFTIME('%W', createdAt) AS INTEGER) + 1) AS sale_week, 
                    SUM(total) AS total_income
                FROM 
                    sales
                WHERE
                    STRFTIME('%Y', createdAt) = ?
                GROUP BY 
                    sale_week
                ORDER BY 
                    sale_week DESC
            """, (year,))
            weekly_sales = cursor.fetchall()  # Fetch all rows from the query result
            conn.close()

            # Populate the table with weekly sales data
            for sale in weekly_sales:
                weekly_sales_table.insert("", "end", values=sale)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch weekly sales analysis: {e}")

    tk.Button(content_frame, text="Fetch Weekly Sales", command=fetch_weekly_sales).pack(pady=10)

def daily_sales_analysis():
    """Display daily sales analysis in the content frame."""
    clear_content_frame()  # Clear the content frame first

    # Configure content frame background
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Daily Sales Analysis", font=("Helvetica", 16), bg="white").pack(pady=10)

    # Treeview for displaying daily sales
    columns = ("Date", "Total Income")
    daily_sales_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    daily_sales_table.pack(fill="both", expand=1, padx=10, pady=10)

    # Define column headings
    for col in columns:
        daily_sales_table.heading(col, text=col)
        daily_sales_table.column(col, anchor="center", width=200)

    # Query daily sales data from the database
    try:
        conn = connect_database()
        cursor = conn.cursor()
        # Aggregate total income by date
        cursor.execute("""
            SELECT 
                DATE(createdAt) AS sale_date, 
                SUM(total) AS total_income
            FROM 
                sales
            GROUP BY 
                DATE(createdAt)
            ORDER BY 
                sale_date DESC
        """)
        daily_sales = cursor.fetchall()  # Fetch all rows from the query result
        conn.close()

        # Populate the table with daily sales data
        for sale in daily_sales:
            daily_sales_table.insert("", "end", values=sale)
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch daily sales analysis: {e}")

    # Add export to CSV button
    def export_to_csv():
        """Export daily sales analysis to a CSV file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV files", "*.csv")], 
            title="Save as"
        )
        if not file_path:
            return  # User canceled the save dialog

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                # Write headers
                writer.writerow(columns)
                # Write data
                for row in daily_sales_table.get_children():
                    writer.writerow(daily_sales_table.item(row)["values"])
            messagebox.showinfo("Export Success", f"Daily sales analysis exported successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export daily sales analysis: {e}")

    tk.Button(content_frame, text="Export to CSV", command=export_to_csv).pack(pady=10)

def manage_inventory():
    """Display the inventory management interface with options for restocking and depleting."""
    clear_content_frame()  # Clear the content frame first

    # Configure content frame background
    content_frame.configure(bg="white")

    # Header
    tk.Label(content_frame, text="Inventory Management", font=("Helvetica", 16), bg="white").pack(pady=10)
    
    # Buttons for restocking and depleting inventory
    button_frame = tk.Frame(content_frame, bg="white")
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Restock Item", command=restock_item,  width=15).grid(row=0, column=0, padx=10)
    tk.Button(button_frame, text="Deplete Item", command=deplete_item,  width=15).grid(row=0, column=1, padx=10)


    # Treeview for displaying inventory records
    columns = ("ID", "Category", "Item", "Quantity", "Created At", "Updated At")
    inventory_table = ttk.Treeview(content_frame, columns=columns, show="headings")
    inventory_table.pack(fill="both", expand=1, padx=10, pady=10)

    # Define column headings
    for col in columns:
        inventory_table.heading(col, text=col)
        inventory_table.column(col, anchor="center", width=150)

    # Query inventory data from the database
    def load_inventory_data():
        """Load inventory data into the treeview."""
        inventory_table.delete(*inventory_table.get_children())  # Clear existing data
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ir.id, 
                    ir.category, 
                    i.name AS item_name, 
                    ir.quantity, 
                    ir.createdAt, 
                    ir.updatedAt
                FROM 
                    inventory_records ir
                JOIN 
                    items i 
                ON 
                    ir.item_id = i.id
                ORDER BY 
                    ir.createdAt DESC
            """)
            records = cursor.fetchall()  # Fetch all rows
            conn.close()

            # Populate the table with inventory records
            for record in records:
                inventory_table.insert("", "end", values=record)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch inventory records: {e}")

    # Initial data load
    load_inventory_data()

# Restock Function
def restock_item():
    #"""Deplete an item in the inventory with a dropdown selection."""
        def submit_restock():
            #"""Handle the restock submission."""
            try:
                selected_item = item_combobox.get()
                quantity = quantity_entry.get()
                notes = notes_entry.get()

                if not selected_item or not quantity:
                    return messagebox.showwarning("Input Error", "All fields are required!")

                try:
                    quantity = int(quantity)  # Ensure quantity is an integer
                except ValueError:
                    return messagebox.showerror("Input Error", "Quantity must be a number!")

                # Extract item_id from the selected item
                item_id = selected_item.split(" - ")[0]

                # Update the database
                conn = connect_database()
                cursor = conn.cursor()

                # Check if the item exists in the inventory
                cursor.execute("SELECT quantity FROM store WHERE item_id = ?", (item_id,))
                existing_record = cursor.fetchone()

                if existing_record:
                    # If the item already exists, update its quantity
                    cursor.execute("""
                        UPDATE store
                        SET quantity = quantity + ?, updatedAt = CURRENT_TIMESTAMP
                        WHERE item_id = ?
                    """, (quantity, item_id))
                else:
                    # If the item doesn't exist, insert a new record  item_id INTEGER NOT NULL
                    cursor.execute("""
                        INSERT INTO store (item_id, quantity) VALUES (?,?)
                    """, (item_id, quantity))
                    
                cursor.execute ("""
                        INSERT INTO inventory_records (category, item_id, quantity, notes)
                        VALUES (?, ?, ?, ?)
                    """, ('Restocking', item_id, quantity, notes))

                conn.commit()
                conn.close()

                messagebox.showinfo("Deplete Success", "Item restocked successfully!")
                load_inventory_data()  # Refresh inventory table
                restock_window.destroy()  # Close the restock window

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to deplete item: {e}")

        # Create a new Toplevel window for restocking
        restock_window = tk.Toplevel()
        restock_window.title("Restock Item")
        restock_window.geometry("600x300")

        # Fetch available items from the database
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM items")
            items = cursor.fetchall()
            conn.close()

            if not items:
                messagebox.showerror("Error", "No items found in the database.")
                restock_window.destroy()
                return

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch items: {e}")
            restock_window.destroy()
            return

        # Label and dropdown for item selection
        tk.Label(restock_window, text="Select Item:").pack(pady=5)
        item_combobox = ttk.Combobox(restock_window, values=[f"{item[0]} - {item[1]}" for item in items], state="readonly")
        item_combobox.pack(pady=5)

        # Entry for quantity
        tk.Label(restock_window, text="Enter Quantity:").pack(pady=5)
        quantity_entry = tk.Entry(restock_window)
        quantity_entry.pack(pady=5)
        
        # Entry for notes
        tk.Label(restock_window, text="Enter notes:").pack(pady=5)
        notes_entry = tk.Entry(restock_window)
        notes_entry.pack(pady=5)

        # Submit button
        tk.Button(restock_window, text="Submit", command=submit_restock).pack(pady=10)

    # Refresh button to reload inventory data
    #tk.Button(content_frame, text="Refresh Inventory", command=load_inventory_data, width=20).pack(pady=10)

# Deplete Function
def deplete_item():
    #"""Deplete an item in the inventory with a dropdown selection."""
        def submit_restock():
            #"""Handle the restock submission."""
            try:
                selected_item = item_combobox.get()
                quantity = quantity_entry.get()
                notes = notes_entry.get()

                if not selected_item or not quantity:
                    return messagebox.showwarning("Input Error", "All fields are required!")

                try:
                    quantity = int(quantity)  # Ensure quantity is an integer
                except ValueError:
                    return messagebox.showerror("Input Error", "Quantity must be a number!")

                # Extract item_id from the selected item
                item_id = selected_item.split(" - ")[0]

                # Update the database
                conn = connect_database()
                cursor = conn.cursor()

                # Check if the item exists in the inventory
                cursor.execute("SELECT quantity FROM store WHERE item_id = ?", (item_id,))
                existing_record = cursor.fetchone()

                if existing_record:
                    # If the item already exists, update its quantity
                    cursor.execute("""
                        UPDATE store
                        SET quantity = quantity - ?, updatedAt = CURRENT_TIMESTAMP
                        WHERE item_id = ?
                    """, (quantity, item_id))
                else:
                    # If the item doesn't exist, insert a new record  item_id INTEGER NOT NULL
                    return messagebox.showerror("Input Error", "Quantity is more than what is in the store")
                    
                cursor.execute ("""
                        INSERT INTO inventory_records (category, item_id, quantity, notes)
                        VALUES (?, ?, ?, ?)
                    """, ('Depleting', item_id, quantity, notes))

                conn.commit()
                conn.close()

                messagebox.showinfo("Deplete Success", "Item depleted successfully!")
                load_inventory_data()  # Refresh inventory table
                restock_window.destroy()  # Close the restock window

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to deplete item: {e}")

        # Create a new Toplevel window for restocking
        restock_window = tk.Toplevel()
        restock_window.title("Deplete Item")
        restock_window.geometry("600x300")

        # Fetch available items from the database
        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM items")
            items = cursor.fetchall()
            conn.close()

            if not items:
                messagebox.showerror("Error", "No items found in the database.")
                restock_window.destroy()
                return

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch items: {e}")
            restock_window.destroy()
            return

        # Label and dropdown for item selection
        tk.Label(restock_window, text="Select Item:").pack(pady=5)
        item_combobox = ttk.Combobox(restock_window, values=[f"{item[0]} - {item[1]}" for item in items], state="readonly")
        item_combobox.pack(pady=5)

        # Entry for quantity
        tk.Label(restock_window, text="Enter Quantity:").pack(pady=5)
        quantity_entry = tk.Entry(restock_window)
        quantity_entry.pack(pady=5)
        
        # Entry for notes
        tk.Label(restock_window, text="Enter notes:").pack(pady=5)
        notes_entry = tk.Entry(restock_window)
        notes_entry.pack(pady=5)

        # Submit button
        tk.Button(restock_window, text="Submit", command=submit_restock).pack(pady=10)

    # Refresh button to reload inventory data
    #tk.Button(content_frame, text="Refresh Inventory", command=load_inventory_data, width=20).pack(pady=10)

#root functions
def clear_content_frame():
    """Clear all widgets in the content frame."""
    for widget in content_frame.winfo_children():
        widget.destroy()


def button_action(name):
    """Handle button actions."""
    if name == "Exit":
        # Confirm exit
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            root.destroy()  # Close the application
    elif name == "Items":
        show_items()
    elif name == "Store":
        manage_inventory()
    elif name == "Stock taking":
        stock_taking()
    elif name == "POS":
        show_pos()
    elif name == "Sales records":
        sales_records()
    elif name == "Daily Sales Income Analysis":
        daily_sales_analysis()
    elif name == "Weekly Sales Income Analysis":
        weekly_sales_analysis()
    elif name == "Monthly Sales Income Analysis":
        monthly_sales_analysis()
    else:
        print(f"Unknown button action: {name}")

def build_GUI():
    global root, content_frame
    
    root = tk.Tk()
    root.title("MEGA-POS")
    root.geometry("1280x720")
    
    #connect to db
    connect_database()
    
    # Create the initial frame
    initial_frame = tk.Frame(root)

    # Heading label in the initial frame
    heading_label = tk.Label(initial_frame, text="Menu", font=("Helvetica", 24))
    heading_label.pack(pady=20)
    
    #button icons
    #products_icn = PhotoImage(file='assets/box-solid.png')
    #store_icn = PhotoImage(file='assets/store-solid.png')
    #cart_icn = PhotoImage(file='assets/cart-shopping-solid (1).png')
    #records_icn = PhotoImage(file='assets/book-solid.png')
    
    #buttons
    buttons = [
        ('Items', None),
        ('Store', None),
        ('Stock taking', None),
        ('POS', None),
        ('Sales records', None),
        ('Daily Sales Income Analysis', None),
        ('Weekly Sales Income Analysis', None),
        ('Monthly Sales Income Analysis', None),
        ('Exit', None)
    ]
    
    # Version number label
    version_label = tk.Label(initial_frame, text="Version 1.0.0", font=("Helvetica", 10), fg="grey")
    version_label.pack(side="bottom", pady=5)
    
    # Add buttons with icons to the frame
    for name, icon in buttons:
        button = tk.Button(initial_frame, text=name, compound="left",
                        command=lambda n=name: button_action(n), height=2, width=20)
        button.pack(fill="x", padx=5, pady=5)
    
    #buttons to the initial frame
    initial_frame.pack(side="left", fill="y")
    content_frame = tk.Frame(root, bg="white")
    content_frame.pack(side="right", fill="both", expand=1)
    # Initially show the initial frame
    #initial_frame.pack(fill="both", expand=1)
    

    # Start the Tkinter event loop
    root.mainloop()
    
# Run the GUI
if __name__ == "__main__":
    build_GUI()