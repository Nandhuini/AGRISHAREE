const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001/api";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  return data;
}

export const getDashboard = () => request("/dashboard");
export const getUsers = ({page=1,limit=100}={}) => request(`/users?limit=${limit}&skip=${(page-1)*limit}`);
export const createUser = data => request("/users", {method:"POST",body:JSON.stringify(data)});
export const updateUser = (id,data) => request(`/users/${id}`, {method:"PUT",body:JSON.stringify(data)});
export const deleteUser = id => request(`/users/${id}`, {method:"DELETE"});

export const getFarmers = ({page=1,limit=100}={}) => request(`/farmers?limit=${limit}&skip=${(page-1)*limit}`);
export const createFarmer = data => request("/farmers", {method:"POST",body:JSON.stringify(data)});
export const updateFarmer = (id,data) => request(`/farmers/${id}`, {method:"PUT",body:JSON.stringify(data)});
export const deleteFarmer = id => request(`/farmers/${id}`, {method:"DELETE"});

export const getEquipment = async (params={}) => {
  const page=params.page||1, limit=params.limit||100, skip=(page-1)*limit;
  const q = params.q ? `?q=${encodeURIComponent(params.q)}&limit=${limit}` : `?limit=${limit}&skip=${skip}`;
  const data = await request(params.q ? `/equipment/search${q}` : `/equipment${q}`);
  return {...data, equipment:(data.equipment||[]).map(item=>({...item,
    name:item.name ?? item.EquipmentName,
    category:item.category ?? item.Brand,
    price_per_day:item.price_per_day ?? item.RentPerDay,
    location:item.location ?? [item.District,item.State].filter(Boolean).join(", "),
    available:item.available ?? (item.Availability === "Available")
  }))};
};
export const getEquipmentSummary = () => request("/equipment/summary");
export const getAvailableEquipment = () => request("/equipment/available");
export const createEquipment = data => request("/equipment",{method:"POST",body:JSON.stringify(data)});
export const updateEquipment = (id,data) => request(`/equipment/${id}`,{method:"PUT",body:JSON.stringify(data)});
export const deleteEquipment = id => request(`/equipment/${id}`,{method:"DELETE"});

export const getBookings = ({page=1,limit=100}={}) => request(`/bookings?limit=${limit}&skip=${(page-1)*limit}`);
export const createBooking = data => request("/bookings",{method:"POST",body:JSON.stringify(data)});
export const cancelBooking = id => request(`/bookings/${id}`,{method:"DELETE"});
export const updateBookingStatus = (id,status) => request(`/bookings/${id}/status`,{method:"PATCH",body:JSON.stringify({status})});

const generic = name => ({
  list:({page=1,limit=100}={})=>request(`/${name}?limit=${limit}&skip=${(page-1)*limit}`),
  create:data=>request(`/${name}`,{method:"POST",body:JSON.stringify(data)}),
  update:(id,data)=>request(`/${name}/${id}`,{method:"PUT",body:JSON.stringify(data)}),
  remove:id=>request(`/${name}/${id}`,{method:"DELETE"})
});
export const produceApi=generic("produce");
export const restaurantsApi=generic("restaurants");
export const ngosApi=generic("ngos");
export const ordersApi=generic("orders");
export const reviewsApi={list:()=>request("/reviews?limit=100"),create:data=>request("/reviews",{method:"POST",body:JSON.stringify(data)}),update:(id,data)=>request(`/reviews/${id}`,{method:"PUT",body:JSON.stringify(data)}),remove:id=>request(`/reviews/${id}`,{method:"DELETE"})};

export const getNotifications=()=>request("/notifications?limit=100");
export const createNotification=data=>request("/notifications",{method:"POST",body:JSON.stringify(data)});
export const markNotificationRead=id=>request(`/notifications/${id}/read`,{method:"PATCH"});
export const markAllNotificationsRead=()=>request("/notifications/read-all",{method:"PATCH"});
export const seedDemo=()=>request("/demo/seed",{method:"POST"});
export async function getCurrentUser(){const data=await getUsers();return data.users?.[0]||null;}

export const getReports=()=>request("/reports");
export const getQueryOptimization=()=>request("/query-optimization");
export const aiSearch=q=>request(`/ai-search?q=${encodeURIComponent(q)}`);
