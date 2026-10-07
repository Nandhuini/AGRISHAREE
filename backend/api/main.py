import os
from datetime import datetime, date
from typing import Any, Optional
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING, DESCENDING

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "AgriConnect")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is missing. Put it in backend/.env")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

app = FastAPI(title="AgriShare API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://agri-share-six.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTIONS = {
    "users": "users",
    "farmers": "farmers",
    "equipment": "equipment",
    "bookings": "equipment_bookings",
    "produce": "produce",
    "restaurants": "restaurants",
    "ngos": "ngos",
    "orders": "orders",
    "reviews": "reviews",
    "notifications": "notifications",
}

def col(name: str):
    return db[COLLECTIONS[name]]

def oid(value: str):
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid id: {value}")

def clean(value: Any):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [clean(x) for x in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    return value

def clean_doc(doc):
    return clean(doc) if doc else None

def pick(doc, *keys, default=None):
    if not isinstance(doc, dict):
        return default
    norm = {str(k).strip().lower().replace(" ", "").replace("_", "").replace("-", ""): v for k, v in doc.items()}
    for key in keys:
        v = norm.get(str(key).strip().lower().replace(" ", "").replace("_", "").replace("-", ""))
        if v is not None and v != "":
            return v
    return default

def location_value(doc):
    direct = pick(doc, "location", "Location", "address", "Address")
    if direct:
        return direct
    district = pick(doc, "District", "district")
    state = pick(doc, "State", "state")
    return ", ".join(str(v) for v in (district, state) if v)

def _lookup_by_id(collection_name: str, value):
    """Resolve Mongo/ObjectId and common legacy identifier fields."""
    if value is None or value == "":
        return None
    vals = [value]
    if isinstance(value, ObjectId):
        vals.append(str(value))
    else:
        try:
            vals.append(ObjectId(str(value)))
        except Exception:
            pass
    # Common identifiers found across the recovered AgriShare datasets.
    keys = [
        "_id", "id", "user_id", "UserID", "UserId", "userid",
        "farmer_id", "FarmerID", "FarmerId", "farmerid",
        "restaurant_id", "RestaurantID", "RestaurantId", "restaurantid",
        "ngo_id", "NGOID", "NgoID", "ngoid",
        "equipment_id", "EquipmentID", "EquipmentId", "equipmentid",
        "produce_id", "ProduceID", "ProduceId", "produceid",
        "surplus_id", "SurplusID", "SurplusId", "surplusid",
        "order_id", "OrderID", "OrderId", "orderid",
        "booking_id", "BookingID", "BookingId", "bookingid",
    ]
    clauses = []
    for k in keys:
        for v in vals:
            clauses.append({k: v})
    try:
        return db[collection_name].find_one({"$or": clauses})
    except Exception:
        return None

def resolve_reference(value, collection_names):
    """Try the same reference against several collections."""
    if value is None or value == "":
        return None, None
    for cname in collection_names:
        doc = _lookup_by_id(cname, value)
        if doc:
            return cname, doc
    return None, None

def normalize_record(name: str, doc: dict):
    """Expose consistent lowercase fields while preserving every original field."""
    item = dict(doc)
    if name == "users":
        item["name"] = pick(doc, "name", "Name", "UserName", "Username", "FullName", default="")
        item["email"] = pick(doc, "email", "Email", default="")
        item["phone"] = pick(doc, "phone", "Phone", "Mobile", default="")
        item["role"] = pick(doc, "role", "Role", "UserRole", "AccountType", default="Member")
    elif name == "farmers":
        item["name"] = pick(doc, "name", "Name", "FarmerName", default="")
        item["phone"] = pick(doc, "phone", "Phone", "Mobile", default="")
        item["email"] = pick(doc, "email", "Email", default="")
        item["location"] = location_value(doc)
        item["crops"] = pick(doc, "crops", "Crops", "PrimaryCrop", "Crop", default=[])
        item["state"] = pick(doc, "State", "state", default="")
        item["district"] = pick(doc, "District", "district", default="")
        item["village"] = pick(doc, "Village", "village", default="")
        item["farm_size"] = pick(doc, "FarmSize(Acres)", "FarmSize", "FarmSizeAcres", default=None)
        item["rating"] = pick(doc, "Rating", "rating", default=None)
    elif name == "equipment":
        item["name"] = pick(doc, "name", "Name", "EquipmentName", "Equipment", default="")
        item["category"] = pick(doc, "category", "Category", "Brand", "EquipmentType", "Type", default="Agricultural Machine")
        item["price_per_day"] = pick(doc, "price_per_day", "PricePerDay", "RentPerDay", "DailyRent", "Price", default=0)
        item["location"] = location_value(doc)
        av = pick(doc, "available", "Available", "Availability", default=True)
        item["available"] = av if isinstance(av, bool) else str(av).strip().lower() in {"available", "true", "yes", "1"}
    elif name == "produce":
        item["name"] = pick(doc, "name", "Name", "Produce", "ProduceName", "Product", "ProductName", "Crop", default="")
        item["farmer_name"] = pick(doc, "farmer_name", "FarmerName", "Farmer", "Farmer_Name", default="")
        item["location"] = location_value(doc)
        item["quantity"] = pick(doc, "quantity", "Quantity", "Qty", default=0)
        item["unit"] = pick(doc, "unit", "Unit", default="kg")
        item["price_per_unit"] = pick(doc, "price_per_unit", "PricePerUnit", "PricePerKg", "Price", default=0)
        item["status"] = pick(doc, "status", "Status", "Availability", default="Available")
    elif name == "restaurants":
        item["name"] = pick(doc, "name", "Name", "Restaurant", "RestaurantName", default="")
        item["location"] = location_value(doc)
        item["cuisine"] = pick(doc, "cuisine", "Cuisine", "CuisineType", default="")
        item["phone"] = pick(doc, "phone", "Phone", "Mobile", default="")
        item["demand"] = pick(doc, "demand", "Demand", "DemandLevel", default="Regular buyer")
    elif name == "ngos":
        # The recovered NGO schema is simpler than the generic admin schema:
        # name, location, contact_person and phone are the reliable fields.
        item["name"] = pick(doc, "name", "Name", "Organization", "OrganizationName", "NGOName", default="")
        item["location"] = location_value(doc)
        item["contact_person"] = pick(doc, "contact_person", "ContactPerson", "Contact", "Coordinator", default="")
        item["phone"] = pick(doc, "phone", "Phone", "Mobile", "ContactPhone", default="")
        item["focus"] = pick(doc, "focus", "Focus", "AreaOfFocus", "Cause", default="")
        item["active_projects"] = pick(doc, "active_projects", "ActiveProjects", "Projects", default=0)
    elif name == "orders":
        item["order_no"] = pick(doc, "order_no", "OrderNo", "OrderNumber", "OrderID", "Order_Id", default="")
        item["produce_name"] = pick(doc, "produce_name", "ProduceName", "Produce", "Product", "ProductName", "Crop", "crop", default="")
        item["buyer"] = pick(doc, "buyer", "Buyer", "BuyerName", "Restaurant", "RestaurantName", "Customer", "CustomerName", default="")
        item["quantity"] = pick(doc, "quantity", "Quantity", "Qty", "OrderQuantity", "OrderedQuantity", "RequestedQuantity", "QuantityOrdered", "TotalQuantity", default=0)
        item["unit"] = pick(doc, "unit", "Unit", "QuantityUnit", default="kg")
        item["total"] = pick(doc, "total", "Total", "TotalAmount", "Amount", "OrderValue", default=0)
        item["status"] = pick(doc, "status", "Status", "OrderStatus", default="Processing")

        buyer_id = pick(doc, "buyer_id", "BuyerId", "BuyerID", "UserId", "UserID", "CustomerId", "CustomerID", "RestaurantId", "RestaurantID")
        surplus_id = pick(doc, "surplus_id", "SurplusId", "SurplusID", "ProduceId", "ProduceID", "Produce_Id")

        if not item["buyer"] and buyer_id:
            _, buyer_doc = resolve_reference(buyer_id, ["users", "restaurants", "farmers"])
            if buyer_doc:
                item["buyer"] = pick(buyer_doc, "name", "Name", "FullName", "Username", "UserName", "RestaurantName", "FarmerName", default="")
                if not item["buyer"]:
                    item["buyer"] = str(buyer_id)

        if not item["produce_name"] and surplus_id:
            _, produce_doc = resolve_reference(surplus_id, ["surplus_produce", "produce"])
            if produce_doc:
                item["produce_name"] = pick(produce_doc, "crop", "Crop", "name", "Name", "produce", "ProduceName", "Product", "ProductName", default="")
                if not item.get("unit") or item["unit"] == "kg":
                    item["unit"] = pick(produce_doc, "unit", "Unit", default=item["unit"])
                if not item.get("quantity"):
                    item["quantity"] = pick(produce_doc, "quantity", "Quantity", "Qty", default=0)
                if not item["produce_name"]:
                    item["produce_name"] = str(surplus_id)

        # Never hide a valid source value just because the related document is missing.
        if not item["buyer"] and buyer_id:
            item["buyer"] = str(buyer_id)
        if not item["produce_name"] and surplus_id:
            item["produce_name"] = str(surplus_id)
        if not item["order_no"]:
            item["order_no"] = str(doc.get("_id", ""))
    elif name == "reviews":
        item["reviewer"] = pick(doc, "reviewer", "Reviewer", "ReviewerName", "User", "UserName", default="")
        item["target"] = pick(doc, "target", "Target", "TargetName", "ReviewTarget", default="")
        item["rating"] = pick(doc, "rating", "Rating", "Stars", default="")
        item["comment"] = pick(doc, "comment", "Comment", "Review", "Feedback", default="")

        user_id = pick(doc, "user_id", "UserId", "UserID", "ReviewerId", "ReviewerID", "ReviewerFarmerID", "ReviewerFarmerId", "FarmerID", "FarmerId")
        order_id = pick(doc, "order_id", "OrderId", "OrderID")
        booking_id = pick(doc, "booking_id", "BookingId", "BookingID")

        if not item["reviewer"] and user_id:
            _, user_doc = resolve_reference(user_id, ["users", "farmers"])
            if user_doc:
                item["reviewer"] = pick(user_doc, "name", "Name", "FullName", "Username", "UserName", "FarmerName", default="")
        if not item["reviewer"] and user_id:
            item["reviewer"] = str(user_id)

        if not item["target"] and booking_id:
            _, booking_doc = resolve_reference(booking_id, ["equipment_bookings", "bookings"])
            if booking_doc:
                equipment_id = pick(booking_doc, "equipment_id", "EquipmentId", "EquipmentID")
                if equipment_id:
                    _, equipment_doc = resolve_reference(equipment_id, ["equipment"])
                    if equipment_doc:
                        item["target"] = pick(equipment_doc, "name", "Name", "EquipmentName", "Equipment", default="")
        if not item["target"] and order_id:
            _, order_doc = resolve_reference(order_id, ["orders"])
            if order_doc:
                item["target"] = pick(order_doc, "produce_name", "ProduceName", "Produce", "Product", "ProductName", "Crop", "crop", default="")
                if not item["target"]:
                    surplus_id = pick(order_doc, "surplus_id", "SurplusId", "SurplusID", "ProduceId", "ProduceID")
                    if surplus_id:
                        _, surplus_doc = resolve_reference(surplus_id, ["surplus_produce", "produce"])
                        if surplus_doc:
                            item["target"] = pick(surplus_doc, "crop", "Crop", "name", "Name", "produce", "ProduceName", default="")
        if not item["target"]:
            # Some imported reviews identify their target directly by type/id.
            target_id = pick(doc, "target_id", "TargetId", "TargetID", "equipment_id", "EquipmentId", "produce_id", "ProduceId")
            target_type = str(pick(doc, "target_type", "TargetType", default="")).lower()
            if target_id:
                candidates = ["equipment", "produce", "surplus_produce"] if "equipment" in target_type else ["produce", "surplus_produce", "equipment"]
                _, target_doc = resolve_reference(target_id, candidates)
                if target_doc:
                    item["target"] = pick(target_doc, "name", "Name", "EquipmentName", "ProduceName", "Produce", "Crop", "crop", default="")
        if not item["target"]:
            item["target"] = str(booking_id or order_id) if (booking_id or order_id) else ""
    return item

def active_filter():
    return {"$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]}

def merge_active(query=None):
    query = query or {}
    return {"$and": [query, active_filter()]}

def now():
    return datetime.utcnow()

class UserIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    role: str = "Member"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None

class FarmerIn(BaseModel):
    name: str
    phone: str
    location: str
    crops: Any = []

class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    crops: Any = None

class EquipmentIn(BaseModel):
    name: str
    category: str = "Agricultural Machine"
    price_per_day: float = Field(gt=0)
    location: str
    owner_id: Optional[str] = None

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price_per_day: Optional[float] = None
    location: Optional[str] = None
    available: Optional[bool] = None

class BookingIn(BaseModel):
    equipment_id: str
    farmer_id: str
    start_date: str
    end_date: str

class StatusIn(BaseModel):
    status: str

class ProduceIn(BaseModel):
    name: str
    farmer_name: str = ""
    location: str = ""
    quantity: float = 0
    unit: str = "kg"
    price_per_unit: float = 0
    status: str = "Available"

class ProduceUpdate(BaseModel):
    name: Optional[str] = None
    farmer_name: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None
    status: Optional[str] = None

class RestaurantIn(BaseModel):
    name: str
    location: str = ""
    cuisine: str = ""
    phone: str = ""
    demand: str = "Regular buyer"

class RestaurantUpdate(RestaurantIn):
    pass

class NGOIn(BaseModel):
    name: str
    location: str = ""
    contact_person: str = ""
    phone: str = ""
    focus: str = ""
    active_projects: int = 0

class NGOUpdate(NGOIn):
    pass

class OrderIn(BaseModel):
    produce_name: str
    buyer: str
    quantity: float
    unit: str = "kg"
    total: float = 0
    status: str = "Processing"

class OrderUpdate(BaseModel):
    produce_name: Optional[str] = None
    buyer: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    total: Optional[float] = None
    status: Optional[str] = None

class ReviewIn(BaseModel):
    reviewer: str
    target: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""

class NotificationIn(BaseModel):
    title: str
    message: str
    kind: str = "info"

@app.get("/")
def root():
    return {"message": "AgriShare API is running", "version": "2.0.0"}

@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        return {"status": "ok", "database": DB_NAME}
    except Exception as exc:
        raise HTTPException(503, f"Database unavailable: {exc}")



def ensure_indexes():
    """Indexes used by the application's frequent filters and report queries."""
    try:
        col("orders").create_index([("FarmerID", ASCENDING)], name="idx_orders_farmer")
        col("orders").create_index([("OrderStatus", ASCENDING)], name="idx_orders_status")
        col("orders").create_index([("OrderDate", DESCENDING)], name="idx_orders_date")
        col("bookings").create_index([("status", ASCENDING)], name="idx_bookings_status")
        col("produce").create_index([("status", ASCENDING)], name="idx_produce_status")
        col("farmers").create_index([("District", ASCENDING)], name="idx_farmers_district")
    except Exception:
        pass


@app.on_event("startup")
def startup_indexes():
    ensure_indexes()


@app.get("/api/reports")
def reports():
    order_status = list(col("orders").aggregate([
        {"$match": active_filter()},
        {"$group": {"_id": {"$ifNull": ["$OrderStatus", "$status"]}, "orders": {"$sum": 1}, "revenue": {"$sum": {"$ifNull": ["$TotalAmount", "$total"]}}}},
        {"$sort": {"orders": -1}}
    ]))
    top_farmers = list(col("orders").aggregate([
        {"$match": active_filter()},
        {"$group": {"_id": {"$ifNull": ["$FarmerID", "$farmer_id"]}, "orders": {"$sum": 1}, "quantity_kg": {"$sum": {"$ifNull": ["$QuantityKG", 0]}}, "revenue": {"$sum": {"$ifNull": ["$TotalAmount", 0]}}}},
        {"$sort": {"quantity_kg": -1}}, {"$limit": 10}
    ]))
    for row in top_farmers:
        fid=row.get("_id")
        farmer=col("farmers").find_one({"FarmerID": fid}) if fid else None
        row["farmer"] = pick(farmer, "Name", "name", default=str(fid or "Unknown")) if farmer else str(fid or "Unknown")
        row.pop("_id", None)
    produce_demand = list(col("orders").aggregate([
        {"$match": active_filter()},
        {"$group": {"_id": {"$ifNull": ["$SurplusID", "$surplus_id"]}, "orders": {"$sum": 1}, "quantity_kg": {"$sum": {"$ifNull": ["$QuantityKG", 0]}}, "revenue": {"$sum": {"$ifNull": ["$TotalAmount", 0]}}}},
        {"$sort": {"quantity_kg": -1}}, {"$limit": 10}
    ]))
    for row in produce_demand:
        sid=row.get("_id")
        prod=col("produce").find_one({"$or":[{"ProduceID":sid},{"SurplusID":sid}]}) if sid else None
        row["produce"] = pick(prod, "Name", "name", "ProduceName", "Product", "Crop", default=str(sid or "Unknown")) if prod else str(sid or "Unknown")
        row.pop("_id", None)
    return {"success": True, "order_status": clean(order_status), "top_farmers": clean(top_farmers), "produce_demand": clean(produce_demand)}


@app.get("/api/query-optimization")
def query_optimization():
    ensure_indexes()
    indexes = {name: list(col(name).list_indexes()) for name in ["orders", "bookings", "produce", "farmers"]}
    compact = {k: [x.get("name") for x in v] for k,v in indexes.items()}
    return {"success": True, "indexes": compact, "note": "Indexes are created for frequent status, farmer, date and district queries."}


@app.get("/api/ai-search")
def ai_search(q: str):
    text=str(q or "").strip().lower()
    if not text:
        return {"success": True, "query": q, "title": "Enter a search", "rows": [], "explanation": "Try: cancelled orders, top farmers, produce demand, or order status."}
    if "cancel" in text or "pending" in text or "completed" in text or "status" in text:
        status = "Cancelled" if "cancel" in text else "Pending" if "pending" in text else "Completed" if "completed" in text else None
        match = {"OrderStatus": status} if status else {}
        rows=list(col("orders").find(merge_active(match)).sort("OrderDate", DESCENDING).limit(20))
        return {"success":True,"query":q,"title":f"{status or 'Order'} orders","rows":clean([normalize_record("orders",x) for x in rows]),"explanation":"Natural-language request mapped to an Orders MongoDB filter."}
    if "farmer" in text and ("top" in text or "best" in text or "quantity" in text):
        rows=list(col("orders").aggregate([{ "$match":active_filter()},{"$group":{"_id":"$FarmerID","orders":{"$sum":1},"quantity_kg":{"$sum":{"$ifNull":["$QuantityKG",0]}},"revenue":{"$sum":{"$ifNull":["$TotalAmount",0]}}}},{"$sort":{"quantity_kg":-1}},{"$limit":5}]))
        for r in rows:
            f=col("farmers").find_one({"FarmerID":r.get("_id")})
            r["farmer"]=pick(f,"Name","name",default=str(r.get("_id"))) if f else str(r.get("_id")); r.pop("_id",None)
        return {"success":True,"query":q,"title":"Top 5 farmers by quantity sold","rows":clean(rows),"explanation":"Natural-language request mapped to a MongoDB aggregation pipeline."}
    if "produce" in text and ("demand" in text or "most" in text or "quantity" in text):
        rows=list(col("orders").aggregate([{ "$match":active_filter()},{"$group":{"_id":"$SurplusID","orders":{"$sum":1},"quantity_kg":{"$sum":{"$ifNull":["$QuantityKG",0]}},"revenue":{"$sum":{"$ifNull":["$TotalAmount",0]}}}},{"$sort":{"quantity_kg":-1}},{"$limit":10}]))
        return {"success":True,"query":q,"title":"Produce demand","rows":clean(rows),"explanation":"Natural-language request mapped to a MongoDB aggregation pipeline."}
    return {"success":True,"query":q,"title":"Search not mapped","rows":[],"explanation":"Supported examples: cancelled orders; pending orders; top farmers by quantity; produce demand."}

@app.get("/api/dashboard")
def dashboard():
    counts = {
        "users": col("users").count_documents(merge_active()),
        "farmers": col("farmers").count_documents(merge_active()),
        "equipment": col("equipment").count_documents(merge_active()),
        "bookings": col("bookings").count_documents(
            merge_active({"status": {"$in": ["Pending", "Confirmed"]}})
        ),
        "produce": col("produce").count_documents(merge_active()),
        "restaurants": col("restaurants").count_documents(merge_active()),
        "ngos": col("ngos").count_documents(merge_active()),
        "orders": col("orders").count_documents(merge_active()),
        "reviews": col("reviews").count_documents(merge_active()),
        "unread_notifications": col("notifications").count_documents(
            merge_active({"read": {"$ne": True}})
        ),
    }
    activity = []
    for name in ["bookings", "orders", "produce", "notifications"]:
        docs = list(col(name).find(active_filter()).sort("created_at", DESCENDING).limit(4))
        for d in docs:
            activity.append({
                "type": name,
                "title": d.get("title") or d.get("produce_name") or d.get("name") or d.get("status") or name,
                "message": d.get("message") or d.get("buyer") or d.get("farmer_name") or "",
                "created_at": d.get("created_at"),
            })
    activity.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"success": True, "counts": counts, "activity": clean(activity[:8])}

# ---------------- Users ----------------
@app.get("/api/users")
def users(limit: int = 100, skip: int = 0):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)
    query = merge_active()
    docs = list(col("users").find(query).sort("name", ASCENDING).skip(skip).limit(limit))
    total = col("users").count_documents(query)
    return {"success": True, "users": [clean_doc(normalize_record("users", x)) for x in docs], "total": total, "limit": limit, "skip": skip}

@app.get("/api/users/{user_id}")
def user(user_id: str):
    doc = col("users").find_one(merge_active({"_id": oid(user_id)}))
    if not doc: raise HTTPException(404, "User not found")
    return {"success": True, "user": clean_doc(doc)}

@app.post("/api/users")
def create_user(data: UserIn):
    doc = data.model_dump()
    doc.update({"created_at": now(), "is_deleted": False})
    result = col("users").insert_one(doc)
    return {"success": True, "user_id": str(result.inserted_id)}

@app.put("/api/users/{user_id}")
def update_user(user_id: str, data: UserUpdate):
    patch = {k:v for k,v in data.model_dump().items() if v is not None}
    if not patch: raise HTTPException(400, "No fields provided")
    result = col("users").update_one({"_id": oid(user_id), **active_filter()}, {"$set": patch})
    if not result.matched_count: raise HTTPException(404, "User not found")
    return {"success": True}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: str):
    result = col("users").update_one({"_id": oid(user_id)}, {"$set": {"is_deleted": True, "updated_at": now()}})
    if not result.matched_count: raise HTTPException(404, "User not found")
    return {"success": True}

# ---------------- Farmers ----------------
@app.get("/api/farmers")
def farmers(limit: int = 100, skip: int = 0):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)
    query = merge_active()
    docs = list(col("farmers").find(query).sort("name", ASCENDING).skip(skip).limit(limit))
    total = col("farmers").count_documents(query)
    return {"success": True, "farmers": [clean_doc(normalize_record("farmers", x)) for x in docs], "total": total, "limit": limit, "skip": skip}

@app.get("/api/farmers/{farmer_id}")
def farmer(farmer_id: str):
    doc = col("farmers").find_one(merge_active({"_id": oid(farmer_id)}))
    if not doc: raise HTTPException(404, "Farmer not found")
    return {"success": True, "farmer": clean_doc(doc)}

@app.post("/api/farmers")
def create_farmer(data: FarmerIn):
    doc = data.model_dump()
    if isinstance(doc["crops"], str):
        doc["crops"] = [x.strip() for x in doc["crops"].split(",") if x.strip()]
    doc.update({"created_at": now(), "is_deleted": False})
    r = col("farmers").insert_one(doc)
    return {"success": True, "farmer_id": str(r.inserted_id)}

@app.put("/api/farmers/{farmer_id}")
def update_farmer(farmer_id: str, data: FarmerUpdate):
    patch = {k:v for k,v in data.model_dump().items() if v is not None}
    if isinstance(patch.get("crops"), str):
        patch["crops"] = [x.strip() for x in patch["crops"].split(",") if x.strip()]
    r = col("farmers").update_one({"_id": oid(farmer_id), **active_filter()}, {"$set": patch})
    if not r.matched_count: raise HTTPException(404, "Farmer not found")
    return {"success": True}

@app.delete("/api/farmers/{farmer_id}")
def delete_farmer(farmer_id: str):
    r = col("farmers").update_one({"_id": oid(farmer_id)}, {"$set": {"is_deleted": True, "updated_at": now()}})
    if not r.matched_count: raise HTTPException(404, "Farmer not found")
    return {"success": True}

# ---------------- Equipment ----------------
@app.get("/api/equipment")
def equipment(limit: int = 100, skip: int = 0):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)
    query = merge_active()
    docs = list(col("equipment").find(query).sort("_id", DESCENDING).skip(skip).limit(limit))
    total = col("equipment").count_documents(query)

    normalized = [clean_doc(normalize_record("equipment", x)) for x in docs]
    return {"success": True, "equipment": normalized, "total": total, "limit": limit, "skip": skip}

@app.get("/api/equipment/summary")
def equipment_summary():
    rows = list(col("equipment").aggregate([
        {"$match": active_filter()},
        {"$group":{"_id":None,"total":{"$sum":1},"available":{"$sum":{"$cond":[{"$ne":["$available",False]},1,0]}},"unavailable":{"$sum":{"$cond":[{"$eq":["$available",False]},1,0]}},"average_price":{"$avg":"$price_per_day"}}}
    ]))
    row=rows[0] if rows else {"total":0,"available":0,"unavailable":0,"average_price":0}
    row.pop("_id",None)
    row["average_price"]=round(row.get("average_price") or 0,2)
    return {"success":True,"summary":row}

@app.get("/api/equipment/{equipment_id}")
def get_equipment(equipment_id: str):
    doc = col("equipment").find_one(merge_active({"_id": oid(equipment_id)}))
    if not doc: raise HTTPException(404, "Equipment not found")
    return {"success": True, "equipment": clean_doc(doc)}

@app.post("/api/equipment")
def create_equipment(data: EquipmentIn):
    doc = data.model_dump()
    if doc.get("owner_id"):
        try: doc["owner_id"] = ObjectId(doc["owner_id"])
        except: doc["owner_id"] = doc["owner_id"]
    doc.update({"available": True, "is_deleted": False, "created_at": now()})
    r = col("equipment").insert_one(doc)
    return {"success": True, "equipment_id": str(r.inserted_id)}

@app.put("/api/equipment/{equipment_id}")
def update_equipment(equipment_id: str, data: EquipmentUpdate):
    patch = {k:v for k,v in data.model_dump().items() if v is not None}
    r = col("equipment").update_one({"_id": oid(equipment_id), **active_filter()}, {"$set": patch})
    if not r.matched_count: raise HTTPException(404, "Equipment not found")
    return {"success": True}

@app.delete("/api/equipment/{equipment_id}")
def delete_equipment(equipment_id: str):
    r = col("equipment").update_one({"_id": oid(equipment_id)}, {"$set": {"is_deleted": True, "available": False, "updated_at": now()}})
    if not r.matched_count: raise HTTPException(404, "Equipment not found")
    return {"success": True}

# ---------------- Booking validation helpers ----------------
def parse_booking_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception:
        raise HTTPException(400, "Dates must use YYYY-MM-DD format")


# ---------------- Bookings ----------------
@app.get("/api/bookings")
def bookings(limit: int = 100, skip: int = 0):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)
    query = merge_active()
    docs = list(col("bookings").find(query).sort("created_at", DESCENDING).skip(skip).limit(limit))
    for d in docs:
        f = None
        e = None
        try: f = col("farmers").find_one({"_id": ObjectId(d.get("farmer_id"))}) if isinstance(d.get("farmer_id"), str) else col("farmers").find_one({"_id": d.get("farmer_id")})
        except: pass
        try: e = col("equipment").find_one({"_id": ObjectId(d.get("equipment_id"))}) if isinstance(d.get("equipment_id"), str) else col("equipment").find_one({"_id": d.get("equipment_id")})
        except: pass
        f_norm = normalize_record("farmers", f) if f else None
        e_norm = normalize_record("equipment", e) if e else None
        d["farmer_name"] = f_norm.get("name") if f_norm else d.get("farmer_name", "Unknown farmer")
        d["equipment_name"] = e_norm.get("name") if e_norm else d.get("equipment_name", "Unknown equipment")
        d["location"] = e_norm.get("location") if e_norm else d.get("location", "")
        d["price_per_day"] = e_norm.get("price_per_day") if e_norm else d.get("price_per_day")
    total = col("bookings").count_documents(query)
    return {"success": True, "bookings": [clean_doc(x) for x in docs], "total": total, "limit": limit, "skip": skip}

@app.post("/api/bookings")
def create_booking(data: BookingIn):
    equipment_id = oid(data.equipment_id)
    farmer_id = oid(data.farmer_id)
    if not col("equipment").find_one(merge_active({"_id": equipment_id})):
        raise HTTPException(404, "Equipment not found")
    if not col("farmers").find_one(merge_active({"_id": farmer_id})):
        raise HTTPException(404, "Farmer not found")
    start = parse_booking_date(data.start_date)
    end = parse_booking_date(data.end_date)
    if start < date.today():
        raise HTTPException(400, "Start date cannot be in the past")
    if end < start:
        raise HTTPException(400, "End date cannot be before start date")
    equipment = col("equipment").find_one(merge_active({"_id": equipment_id}))
    if not equipment:
        raise HTTPException(404, "Equipment not found")
    if equipment.get("available") is False:
        raise HTTPException(409, "Equipment is currently unavailable")
    overlap = {
        "equipment_id": {"$in": [equipment_id, str(equipment_id)]},
        "status": {"$in": ["Pending", "Confirmed"]},
        "start_date": {"$lte": data.end_date},
        "end_date": {"$gte": data.start_date},
        "$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}],
    }
    if col("bookings").find_one(overlap):
        raise HTTPException(409, "Equipment is already booked for those dates")
    e = equipment
    doc = {
        "equipment_id": equipment_id,
        "farmer_id": farmer_id,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "status": "Pending",
        "price_per_day": e.get("price_per_day") if e else 0,
        "created_at": now(),
        "is_deleted": False,
    }
    r = col("bookings").insert_one(doc)
    col("notifications").insert_one({
        "title": "Booking created",
        "message": f"New {e.get('name','equipment')} booking request created.",
        "kind": "booking",
        "read": False,
        "created_at": now(),
        "is_deleted": False,
    })
    return {"success": True, "booking_id": str(r.inserted_id)}

@app.patch("/api/bookings/{booking_id}/status")
def booking_status(booking_id: str, data: StatusIn):
    if data.status not in ["Pending", "Confirmed", "Completed", "Cancelled"]:
        raise HTTPException(400, "Invalid booking status")
    r = col("bookings").update_one({"_id": oid(booking_id), **active_filter()}, {"$set": {"status": data.status, "updated_at": now()}})
    if not r.matched_count: raise HTTPException(404, "Booking not found")
    return {"success": True}

@app.delete("/api/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    r = col("bookings").update_one({"_id": oid(booking_id), **active_filter()}, {"$set": {"status": "Cancelled", "updated_at": now()}})
    if not r.matched_count: raise HTTPException(404, "Booking not found")
    return {"success": True}

# ---------------- Generic modules ----------------
def generic_list(name, limit: int = 100, skip: int = 0):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)
    query = merge_active()

    # The recovered NGO database contains repeated copies of the exact same
    # organization record (created by the original NGO service script being
    # executed multiple times). Keep one real record per organization instead
    # of displaying the same NGO hundreds of times.
    if name == "ngos":
        docs = list(col(name).find(query).sort("_id", DESCENDING))
        seen = set()
        unique = []
        for doc in docs:
            item = normalize_record(name, doc)
            key = (
                str(item.get("name", "")).strip().lower(),
                str(item.get("location", "")).strip().lower(),
                str(item.get("contact_person", "")).strip().lower(),
                str(item.get("phone", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(clean_doc(item))
        total = len(unique)
        return {
            "success": True,
            "items": unique[skip:skip + limit],
            "total": total,
            "limit": limit,
            "skip": skip
        }

    docs = list(
        col(name).find(query).sort("_id", DESCENDING).skip(skip).limit(limit)
    )
    total = col(name).count_documents(query)
    return {
        "success": True,
        "items": [clean_doc(normalize_record(name, x)) for x in docs],
        "total": total,
        "limit": limit,
        "skip": skip
    }

def generic_get(name, item_id):
    d = col(name).find_one(merge_active({"_id": oid(item_id)}))
    if not d: raise HTTPException(404, "Record not found")
    return {"success": True, "item": clean_doc(d)}

def generic_create(name, payload):
    payload = dict(payload)
    payload.update({"created_at": now(), "is_deleted": False})
    r = col(name).insert_one(payload)
    return {"success": True, "id": str(r.inserted_id)}

def generic_update(name, item_id, payload):
    patch = {k:v for k,v in payload.items() if v is not None}
    r = col(name).update_one({"_id": oid(item_id), **active_filter()}, {"$set": patch})
    if not r.matched_count: raise HTTPException(404, "Record not found")
    return {"success": True}

def generic_delete(name, item_id):
    r = col(name).update_one({"_id": oid(item_id)}, {"$set": {"is_deleted": True, "updated_at": now()}})
    if not r.matched_count: raise HTTPException(404, "Record not found")
    return {"success": True}

# Produce
@app.get("/api/produce")
def list_produce(limit: int = 100, skip: int = 0): return generic_list("produce", limit, skip)
@app.post("/api/produce")
def create_produce(data: ProduceIn): return generic_create("produce", data.model_dump())
@app.put("/api/produce/{item_id}")
def update_produce(item_id: str, data: ProduceUpdate): return generic_update("produce", item_id, data.model_dump())
@app.delete("/api/produce/{item_id}")
def delete_produce(item_id: str): return generic_delete("produce", item_id)

# Restaurants
@app.get("/api/restaurants")
def list_restaurants(limit: int = 100, skip: int = 0): return generic_list("restaurants", limit, skip)
@app.post("/api/restaurants")
def create_restaurant(data: RestaurantIn): return generic_create("restaurants", data.model_dump())
@app.put("/api/restaurants/{item_id}")
def update_restaurant(item_id: str, data: RestaurantUpdate): return generic_update("restaurants", item_id, data.model_dump())
@app.delete("/api/restaurants/{item_id}")
def delete_restaurant(item_id: str): return generic_delete("restaurants", item_id)

# NGOs
@app.get("/api/ngos")
def list_ngos(limit: int = 100, skip: int = 0): return generic_list("ngos", limit, skip)
@app.post("/api/ngos")
def create_ngo(data: NGOIn): return generic_create("ngos", data.model_dump())
@app.put("/api/ngos/{item_id}")
def update_ngo(item_id: str, data: NGOUpdate): return generic_update("ngos", item_id, data.model_dump())
@app.delete("/api/ngos/{item_id}")
def delete_ngo(item_id: str): return generic_delete("ngos", item_id)

# Orders
@app.get("/api/orders")
def list_orders(limit: int = 100, skip: int = 0): return generic_list("orders", limit, skip)
@app.post("/api/orders")
def create_order(data: OrderIn): return generic_create("orders", data.model_dump())
@app.put("/api/orders/{item_id}")
def update_order(item_id: str, data: OrderUpdate): return generic_update("orders", item_id, data.model_dump())
@app.delete("/api/orders/{item_id}")
def delete_order(item_id: str): return generic_delete("orders", item_id)

# Reviews
@app.get("/api/reviews")
def list_reviews(limit: int = 100, skip: int = 0): return generic_list("reviews", limit, skip)
@app.post("/api/reviews")
def create_review(data: ReviewIn): return generic_create("reviews", data.model_dump())
@app.put("/api/reviews/{item_id}")
def update_review(item_id: str, data: ReviewIn):
    return generic_update("reviews", item_id, data.model_dump())

@app.delete("/api/reviews/{item_id}")
def delete_review(item_id: str): return generic_delete("reviews", item_id)

# Notifications
@app.get("/api/notifications")
def list_notifications():
    docs = list(col("notifications").find(merge_active()).sort("created_at", DESCENDING).limit(50))
    return {"success": True, "notifications": [clean_doc(x) for x in docs]}

@app.post("/api/notifications")
def create_notification(data: NotificationIn): return generic_create("notifications", {**data.model_dump(), "read": False})

@app.patch("/api/notifications/{item_id}/read")
def mark_notification_read(item_id: str):
    r = col("notifications").update_one({"_id": oid(item_id), **active_filter()}, {"$set": {"read": True}})
    if not r.matched_count: raise HTTPException(404, "Notification not found")
    return {"success": True}

@app.patch("/api/notifications/read-all")
def mark_all_notifications_read():
    col("notifications").update_many(merge_active({"read": {"$ne": True}}), {"$set": {"read": True}})
    return {"success": True}

# ---------------- Demo data ----------------
@app.post("/api/demo/seed")
def seed_demo():
    # Never delete or overwrite existing records. Only fill empty collections.
    inserted = {}
    if col("users").count_documents(merge_active()) == 0:
        r = col("users").insert_one({
            "name": "Nandu", "email": "nandu@example.com", "phone": "", "role": "Member",
            "created_at": now(), "is_deleted": False
        })
        inserted["users"] = 1

    if col("farmers").count_documents(merge_active()) < 4:
        existing_names = {x.get("name") for x in col("farmers").find(merge_active(), {"name": 1})}
        docs = [
            {"name":"Kumar Farms","phone":"9876500001","location":"Coimbatore","crops":["Onion","Coconut"]},
            {"name":"Green Valley Farm","phone":"9876500002","location":"Pollachi","crops":["Coconut","Banana"]},
            {"name":"Muthu Agro","phone":"9876500003","location":"Tiruppur","crops":["Banana","Tomato"]},
        ]
        docs = [dict(x, created_at=now(), is_deleted=False) for x in docs if x["name"] not in existing_names]
        if docs: col("farmers").insert_many(docs)
        inserted["farmers"] = len(docs)

    if col("produce").count_documents(merge_active()) == 0:
        docs = [
            {"name":"Tomato","farmer_name":"Test Farmer JR","location":"Pollachi","quantity":500,"unit":"kg","price_per_unit":38,"status":"Available"},
            {"name":"Onion","farmer_name":"Kumar Farms","location":"Coimbatore","quantity":800,"unit":"kg","price_per_unit":32,"status":"Available"},
            {"name":"Coconut","farmer_name":"Green Valley Farm","location":"Pollachi","quantity":1200,"unit":"units","price_per_unit":28,"status":"Available"},
            {"name":"Banana","farmer_name":"Muthu Agro","location":"Tiruppur","quantity":650,"unit":"kg","price_per_unit":45,"status":"Limited"},
        ]
        col("produce").insert_many([dict(x, created_at=now(), is_deleted=False) for x in docs])
        inserted["produce"] = len(docs)

    if col("restaurants").count_documents(merge_active()) == 0:
        docs = [
            {"name":"Green Leaf Restaurant","location":"Coimbatore","cuisine":"South Indian","phone":"+91 98765 10001","demand":"High demand"},
            {"name":"Farm Table","location":"Pollachi","cuisine":"Farm-to-table","phone":"+91 98765 10002","demand":"Regular buyer"},
            {"name":"Harvest Kitchen","location":"Tiruppur","cuisine":"Multi-cuisine","phone":"+91 98765 10003","demand":"New partner"},
            {"name":"Agro Bistro","location":"Chennai","cuisine":"Healthy dining","phone":"+91 98765 10004","demand":"Regular buyer"},
        ]
        col("restaurants").insert_many([dict(x, created_at=now(), is_deleted=False) for x in docs])
        inserted["restaurants"] = len(docs)

    if col("ngos").count_documents(merge_active()) == 0:
        docs = [
            {"name":"Green Earth Foundation","focus":"Sustainable farming","location":"Coimbatore","active_projects":8},
            {"name":"Rural Growth Initiative","focus":"Farmer support","location":"Pollachi","active_projects":12},
            {"name":"AgriCare Trust","focus":"Food security","location":"Chennai","active_projects":6},
            {"name":"Water & Soil Mission","focus":"Water conservation","location":"Tiruppur","active_projects":5},
        ]
        col("ngos").insert_many([dict(x, created_at=now(), is_deleted=False) for x in docs])
        inserted["ngos"] = len(docs)

    if col("orders").count_documents(merge_active()) == 0:
        docs = [
            {"order_no":"ORD-1001","produce_name":"Tomato","buyer":"Green Leaf Restaurant","quantity":100,"unit":"kg","total":3800,"status":"Processing"},
            {"order_no":"ORD-1002","produce_name":"Onion","buyer":"Coimbatore Fresh Market","quantity":200,"unit":"kg","total":6400,"status":"Confirmed"},
            {"order_no":"ORD-1003","produce_name":"Coconut","buyer":"Pollachi Foods","quantity":150,"unit":"units","total":4200,"status":"Delivered"},
        ]
        col("orders").insert_many([dict(x, created_at=now(), is_deleted=False) for x in docs])
        inserted["orders"] = len(docs)

    if col("notifications").count_documents(merge_active()) == 0:
        docs = [
            {"title":"Booking confirmed","message":"Your Harvester booking has been confirmed.","kind":"booking","read":False},
            {"title":"New produce available","message":"Fresh tomatoes are available from Pollachi.","kind":"produce","read":False},
            {"title":"Order delivered","message":"Order ORD-1003 has been marked delivered.","kind":"order","read":True},
            {"title":"Community update","message":"Green Earth Foundation added a new project.","kind":"community","read":True},
        ]
        col("notifications").insert_many([dict(x, created_at=now(), is_deleted=False) for x in docs])
        inserted["notifications"] = len(docs)

    return {"success": True, "inserted": inserted}
