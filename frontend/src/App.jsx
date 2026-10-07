import { useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard, Users, Tractor, CalendarDays, ShoppingBasket, ClipboardList,
  Building2, HeartHandshake, Star, Bell, Menu, X, MapPin, IndianRupee,
  BarChart3, Sparkles, DatabaseZap,
  RefreshCw, Sprout, Phone, Mail, Plus, Pencil, Trash2, Check, ChevronDown,
  Package, UserRound, Settings, LogOut, Search, AlertCircle, CheckCircle2
} from "lucide-react";
import * as api from "./services/api";
import "./App.css";

const pages = [
  ["Dashboard", LayoutDashboard], ["Reports", BarChart3], ["AI Search", Sparkles], ["Farmers", Users], ["Equipment", Tractor],
  ["Bookings", CalendarDays], ["Produce", ShoppingBasket], ["Orders", ClipboardList],
  ["Restaurants", Building2], ["NGOs", HeartHandshake], ["Reviews", Star],
  ["Notifications", Bell], ["Users", UserRound],
];

const emptyForms = {
  Farmers:{name:"",phone:"",location:"",crops:""},
  Equipment:{name:"",category:"Agricultural Machine",price_per_day:"",location:""},
  Produce:{name:"",farmer_name:"",location:"",quantity:"",unit:"kg",price_per_unit:"",status:"Available"},
  Restaurants:{name:"",location:"",cuisine:"",phone:"",demand:"Regular buyer"},
  Orders:{order_no:"",produce_name:"",buyer:"",quantity:"",unit:"kg",total:"",status:"Processing"},
  NGOs:{name:"",location:"",contact_person:"",phone:"",focus:"",active_projects:""},
  Orders:{produce_name:"",buyer:"",quantity:"",unit:"kg",total:"",status:"Processing"},
  Users:{name:"",email:"",phone:"",role:"Member"},
};

function App() {
  const [role,setRole] = useState(localStorage.getItem("agrishare_role") || "");
  const chooseRole = (next) => { localStorage.setItem("agrishare_role", next); setRole(next); };
  const [page,setPage] = useState("Dashboard");
  const [mobile,setMobile] = useState(false);
  const [dashboard,setDashboard] = useState(null);
  const [user,setUser] = useState(null);
  const [notifications,setNotifications] = useState([]);
  const [bellOpen,setBellOpen] = useState(false);
  const [profileOpen,setProfileOpen] = useState(false);

  async function refreshGlobal() {
    try {
      const [d,u,n] = await Promise.all([api.getDashboard(),api.getUsers({page:1,limit:1}),api.getNotifications()]);
      setDashboard(d); setUser(u.users?.[0] || null); setNotifications(n.notifications || []);
    } catch(e) { console.error(e); }
  }
  useEffect(()=>{refreshGlobal()},[]);
  const unread = notifications.filter(n=>!n.read).length;
  const go = (p)=>{setPage(p);setMobile(false);setBellOpen(false);setProfileOpen(false)};
  async function markRead(id) { await api.markNotificationRead(id); await refreshGlobal(); }
  async function markAllRead() { await api.markAllNotificationsRead(); await refreshGlobal(); }
  if (!role) return <RoleGate onChoose={chooseRole}/>;
  if (role === "User") return <UserPortal onAdmin={()=>chooseRole("Admin")} onLogout={()=>{localStorage.removeItem("agrishare_role");setRole("")}}/>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobile?"open":""}`}>
      <div className="brand"><div className="brand-mark">A</div><div><b>AgriShare</b><small>AgriShare Administration</small></div></div>
      <nav>{pages.map(([name,Icon])=><button key={name} className={`nav-item ${page===name?"active":""}`} onClick={()=>go(name)}><Icon size={18}/><span>{name}</span></button>)}</nav>
    </aside>
    {mobile && <div className="scrim" onClick={()=>setMobile(false)}/>}
    <main className="main">
      <header className="topbar">
        <button className="mobile-menu" onClick={()=>setMobile(v=>!v)}>{mobile?<X/>:<Menu/>}</button>
        <div><h1>{page}</h1><p>AgriShare Admin Portal</p></div>
        <div className="top-actions">
          <div className="relative"><button className="icon-btn" onClick={()=>{setBellOpen(v=>!v);setProfileOpen(false)}}><Bell size={19}/>{unread>0&&<span className="badge">{unread}</span>}</button>{bellOpen&&<NotificationPopover notifications={notifications} onRead={markRead} onAll={markAllRead} onView={()=>go("Notifications")}/>}</div>
          <div className="relative"><button className="profile-trigger" onClick={()=>{setProfileOpen(v=>!v);setBellOpen(false)}}><div className="avatar">{(user?.name||"N").charAt(0).toUpperCase()}</div><div className="profile-text"><b>{user?.name||"Nandu"}</b><span>Admin</span></div><ChevronDown size={15}/></button>{profileOpen&&<ProfileMenu user={user} onUsers={()=>go("Users")} onRefresh={refreshGlobal}/>}</div>
          <button className="secondary" onClick={()=>{localStorage.removeItem("agrishare_role");setRole("")}}>Switch role</button>
        </div>
      </header>
      <div className="content">{renderPage(page,{dashboard,user,notifications,refreshGlobal,go})}</div>
    </main>
  </div>;
}

function RoleGate({onChoose}) {
  return <div style={{minHeight:"100vh",display:"grid",placeItems:"center",background:"#f5f7f3",padding:24}}>
    <div className="panel" style={{width:"min(760px,100%)",padding:40,textAlign:"center"}}>
      <div className="brand-mark" style={{margin:"0 auto 18px"}}>A</div>
      <span className="eyebrow">AGRISHARE</span><h1 style={{margin:"8px 0"}}>Choose your portal</h1>
      <p className="muted">The interface and permissions change according to the selected role.</p>
      <div style={{display:"grid",gridTemplateColumns:"repeat(2,minmax(0,1fr))",gap:16,marginTop:28}}>
        <button className="primary" style={{padding:22}} onClick={()=>onChoose("Admin")}><strong>Admin Portal</strong><small style={{display:"block",marginTop:6}}>Full system management, reports and AI tools</small></button>
        <button className="secondary" style={{padding:22}} onClick={()=>onChoose("User")}><strong>User Portal</strong><small style={{display:"block",marginTop:6}}>Browse equipment, search and manage bookings</small></button>
      </div>
      <p style={{fontSize:12,marginTop:18}} className="muted">Review build: role separation is active; production authentication can be added after the review.</p>
    </div>
  </div>;
}

function UserPortal({onAdmin,onLogout}) {
  const [equipment,setEquipment]=useState([]),[bookings,setBookings]=useState([]),[farmers,setFarmers]=useState([]),[q,setQ]=useState(""),[loading,setLoading]=useState(true),[error,setError]=useState(""),[selected,setSelected]=useState(null),[dates,setDates]=useState({start_date:"",end_date:""}),[farmerId,setFarmerId]=useState("");
  const load=async()=>{try{setLoading(true);const [e,b,f]=await Promise.all([api.getEquipment(),api.getBookings(),api.getFarmers()]);setEquipment(e.equipment||[]);setBookings(b.bookings||[]);setFarmers(f.farmers||[]);setFarmerId(f.farmers?.[0]?._id||"")}catch(e){setError(e.message)}finally{setLoading(false)}};
  useEffect(()=>{load()},[]);
  const terms=q.toLowerCase().split(/\s+/).filter(Boolean);
  const filtered=equipment.filter(x=>!terms.length||terms.every(t=>JSON.stringify(x).toLowerCase().includes(t)));
  const aiHint=terms.length ? `AI search interpreted: ${terms.join(", ")}` : "AI-assisted search: describe the machine, location or use you need.";
  async function book(){try{if(!selected||!dates.start_date||!dates.end_date||!farmerId)throw new Error("Select equipment, farmer and valid dates.");await api.createBooking({equipment_id:selected._id,farmer_id:farmerId,...dates});setSelected(null);setDates({start_date:"",end_date:""});await load()}catch(e){setError(e.message)}}
  return <div style={{maxWidth:1200,margin:"0 auto"}}>
    <div className="hero"><div><span className="eyebrow">USER PORTAL</span><h2>Find. Book. Grow.</h2><p>Search agricultural equipment and manage your bookings from one place.</p></div><div className="hero-icon"><Tractor size={46}/></div></div>
    <div className="panel" style={{padding:20,marginTop:18}}><div className="search" style={{maxWidth:"100%"}}><Search size={18}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Try: tractor Chennai 3 days"/></div><small className="muted" style={{display:"block",marginTop:10}}>{aiHint}</small></div>
    {error&&<ErrorBox text={error}/>}<div style={{display:"flex",justifyContent:"space-between",alignItems:"center",margin:"24px 0 12px"}}><div><span className="eyebrow">AVAILABLE EQUIPMENT</span><h3 style={{margin:"5px 0"}}>{filtered.length} matches</h3></div><div><button className="secondary" onClick={onAdmin}>Admin portal</button> <button className="secondary" onClick={onLogout}>Logout</button></div></div>
    {loading?<Loading/>:<div className="card-grid">{filtered.slice(0,24).map(x=><article className="panel" style={{padding:20}} key={x._id}><span className="status-chip confirmed">{x.available===false?"Unavailable":"Available"}</span><h3>{x.name}</h3><p className="muted">{x.category||"Agricultural Machine"} · {x.location||"—"}</p><strong>{x.price_per_day||0}/day</strong><div style={{marginTop:16}}><button className="primary" disabled={x.available===false} onClick={()=>setSelected(x)}>Book equipment</button></div></article>)}</div>}
    {!loading&&!filtered.length&&<Empty text="No equipment matches your search."/>}
    <div className="panel" style={{padding:20,marginTop:24}}><span className="eyebrow">MY BOOKINGS</span><h3>Recent bookings</h3>{bookings.slice(0,8).map(b=><div className="activity" key={b._id}><div><b>{b.equipment_name||"Equipment"}</b><small>{b.start_date} → {b.end_date} · {b.status}</small></div></div>)}{!bookings.length&&<Empty text="No bookings yet."/>}</div>
    {selected&&<div className="modal-backdrop"><div className="modal"><div className="modal-head"><h3>Book {selected.name}</h3><button onClick={()=>setSelected(null)}><X/></button></div><div className="form-grid"><label>Farmer<select value={farmerId} onChange={e=>setFarmerId(e.target.value)}>{farmers.slice(0,100).map(f=><option key={f._id} value={f._id}>{f.name}</option>)}</select></label><label>Start date<input type="date" value={dates.start_date} onChange={e=>setDates({...dates,start_date:e.target.value})}/></label><label>End date<input type="date" min={dates.start_date||undefined} value={dates.end_date} onChange={e=>setDates({...dates,end_date:e.target.value})}/></label></div><div className="modal-actions"><button className="secondary" onClick={()=>setSelected(null)}>Cancel</button><button className="primary" onClick={book}>Create booking</button></div></div></div>}
  </div>;
}

function NotificationPopover({notifications,onRead,onAll,onView}) {
  return <div className="popover notification-pop">
    <div className="popover-head"><b>Notifications</b><button onClick={onAll}>Mark all read</button></div>
    {notifications.slice(0,5).map(n=><button className={`notice-row ${n.read?"":"unread"}`} key={n._id} onClick={()=>!n.read&&onRead(n._id)}>
      <Bell size={16}/><span><b>{n.title}</b><small>{n.message}</small></span>
    </button>)}
    {notifications.length===0&&<div className="muted pad">No notifications</div>}
    <button className="view-all" onClick={onView}>View all notifications</button>
  </div>
}
function ProfileMenu({user,onUsers,onRefresh}) {
  return <div className="popover profile-pop">
    <div className="profile-summary"><div className="avatar large">{(user?.name||"U").charAt(0).toUpperCase()}</div><div><b>{user?.name||"Nandu"}</b><span>Administrator</span></div></div>
    <button onClick={onUsers}><UserRound size={16}/> Manage users</button>
    <button onClick={onRefresh}><RefreshCw size={16}/> Refresh profile</button>
  </div>
}

function DashboardPage({dashboard,go}) {
  if(!dashboard) return <Loading/>;
  const c=dashboard.counts;
  const stats=[
    ["Farmers",c.farmers,Users,"Registered farmers"],["Equipment",c.equipment,Tractor,"Equipment records"],
    ["Bookings",c.bookings,CalendarDays,"Pending / confirmed"],["Produce",c.produce,ShoppingBasket,"Active listings"],
    ["Restaurants",c.restaurants,Building2,"Network buyers"],["NGOs",c.ngos,HeartHandshake,"Partner organizations"],
  ];
  return <section>
    <div className="hero"><div><span className="eyebrow">AGRICULTURAL NETWORK</span><h2>Connect. Share. Grow.</h2><p>One place to manage farmers, equipment, produce and community connections.</p></div><div className="hero-icon"><Tractor size={46}/></div></div>
    <div className="stats-grid">{stats.map(([label,value,Icon,desc])=><div className="stat" key={label}><div className="stat-icon"><Icon size={20}/></div><div><span>{label}</span><strong>{value}</strong><small>{desc}</small></div></div>)}</div>
    <div className="dash-grid">
      <div className="panel"><div className="panel-title"><div><span className="eyebrow">RECENT ACTIVITY</span><h3>Latest activity</h3></div></div>
        {dashboard.activity?.length?<div className="activity-list">{dashboard.activity.map((a,i)=><button className="activity" key={i} onClick={()=>{
              const target={bookings:"Bookings",orders:"Orders",produce:"Produce",notifications:"Notifications"}[a.type];
              if(target) go(target);
            }}><span className="dot"/><div><b>{a.title}</b><small>{a.message||a.type}</small></div></button>)}</div>:<Empty text="No activity yet"/>}
      </div>
      <div className="panel"><div className="panel-title"><div><span className="eyebrow">QUICK ACTIONS</span><h3>Get started</h3></div></div>
        <div className="quick"><button onClick={()=>go("Farmers")}><Users/> Farmers</button><button onClick={()=>go("Equipment")}><Tractor/> Equipment</button><button onClick={()=>go("Produce")}><ShoppingBasket/> Produce</button><button onClick={()=>go("Bookings")}><CalendarDays/> Bookings</button></div>
      </div>
    </div>
  </section>
}

function DataPage({title,icon:Icon,items,setItems,fields,apiObj,searchPlaceholder,extraHeader}) {
  const [loading,setLoading]=useState(true),[error,setError]=useState(""),[search,setSearch]=useState(""),
        [editing,setEditing]=useState(null),[form,setForm]=useState(emptyForms[title]||{}),
        [saving,setSaving]=useState(false),[formOpen,setFormOpen]=useState(false),
        [page,setPage]=useState(1),[pageSize,setPageSize]=useState(50),[total,setTotal]=useState(0);

  const load=async(nextPage=page,nextSize=pageSize)=>{
    try{
      setLoading(true); setError("");
      const d=await apiObj.list({page:nextPage,limit:nextSize});
      setItems(d.items || d.equipment || d.farmers || d.users || d.produce || d.restaurants || d.ngos || d.orders || d.reviews || d.notifications || []);
      setTotal(Number(d.total ?? (d.items||[]).length));
      setPage(nextPage); setPageSize(nextSize);
    }catch(e){setError(e.message)}
    finally{setLoading(false)}
  };
  useEffect(()=>{load(1,pageSize)},[title]);

  const filtered=items.filter(x=>JSON.stringify(x).toLowerCase().includes(search.toLowerCase()));
  function start(item=null){setEditing(item?item._id:null);setForm(item?{...emptyForms[title],...item}:{...(emptyForms[title]||{})});setFormOpen(true)}
  async function save(e){
    e.preventDefault();setSaving(true);
    try{
      const payload={...form};
      if(title==="Produce"||title==="Equipment"){
        for(const k of ["quantity","price_per_unit","price_per_day","active_projects"])
          if(payload[k]!==undefined&&payload[k]!=="")payload[k]=Number(payload[k])
      }
      if(editing) await apiObj.update(editing,payload); else await apiObj.create(payload);
      setEditing(null);setFormOpen(false);await load(page,pageSize)
    }catch(e){setError(e.message)}
    finally{setSaving(false)}
  }
  async function remove(id){
    if(!confirm("Delete this record?"))return;
    try{await apiObj.remove(id);await load(page,pageSize)}catch(e){setError(e.message)}
  }

  const first=total===0?0:(page-1)*pageSize+1;
  const last=Math.min(page*pageSize,total);
  const pages=Math.max(1,Math.ceil(total/pageSize));

  return <section>
    <div className="page-head"><div><span className="eyebrow">{title.toUpperCase()} MANAGEMENT</span><h2>{title}</h2><p>Live records from the AgriShare database.</p></div><button className="primary" onClick={()=>start()}><Plus size={17}/> Add {title.slice(0,-1)||title}</button></div>
    {error&&<ErrorBox text={error}/>}
    <div className="toolbar">
      <div className="search"><Search size={17}/><input placeholder={searchPlaceholder||`Search this page of ${title.toLowerCase()}...`} value={search} onChange={e=>setSearch(e.target.value)}/></div>
      <button className="secondary" onClick={()=>load(page,pageSize)}><RefreshCw size={16}/> Refresh</button>
    </div>
    {formOpen && <FormModal title={`${editing?"Edit":"Add"} ${title}`} fields={fields} form={form} setForm={setForm} onClose={()=>{setFormOpen(false);setEditing(null)}} onSubmit={save} saving={saving}/>}
    {loading?<Loading/>:<div className="cards">{filtered.map(item=><article className="card" key={item._id}>
      <div className="card-icon"><Icon size={23}/></div><div className="card-body">
      <div className="card-top"><span className="eyebrow">{title.slice(0,-1)||title}</span><span className="status-chip">{item.status||item.demand||"Active"}</span></div>
      <h3>{item.name||item.produce_name||item.order_no||item.target||"Record"}</h3>
      <div className="facts">{fields.slice(0,4).map(f=><div key={f.key}><small>{f.label}</small><b>{formatValue(item[f.key])}</b></div>)}</div>
      <div className="card-actions"><button onClick={()=>start(item)}><Pencil size={15}/> Edit</button><button className="danger-text" onClick={()=>remove(item._id)}><Trash2 size={15}/> Delete</button></div>
      </div></article>)}</div>}
    {!loading&&filtered.length===0&&<Empty text={`No ${title.toLowerCase()} found on this page.`}/>}
    {!loading&&<div className="pagination-bar">
      <div><b>{first}–{last}</b> of <b>{total.toLocaleString()}</b> records</div>
      <div className="pagination-controls">
        <label>Rows <select value={pageSize} onChange={e=>load(1,Number(e.target.value))}><option value="25">25</option><option value="50">50</option><option value="100">100</option></select></label>
        <button className="secondary" disabled={page<=1} onClick={()=>load(page-1,pageSize)}>Previous</button>
        <span>Page {page} of {pages}</span>
        <button className="secondary" disabled={page>=pages} onClick={()=>load(page+1,pageSize)}>Next</button>
      </div>
    </div>}
  </section>
}

function FormModal({title,fields,form,setForm,onClose,onSubmit,saving}) {
  return <div className="modal-backdrop"><form className="modal" onSubmit={onSubmit}><div className="modal-head"><h3>{title}</h3><button type="button" onClick={onClose}><X/></button></div>
    <div className="form-grid">{fields.map(f=><label key={f.key}>{f.label}<input required={f.required!==false} type={f.type||"text"} value={form[f.key]??""} onChange={e=>setForm({...form,[f.key]:e.target.value})}/></label>)}</div>
    <div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={saving}>{saving?"Saving...":"Save"}</button></div>
  </form></div>
}
function formatValue(v){
  if(Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if(v===undefined || v===null || v==="") return "—";
  if(typeof v === "object") return JSON.stringify(v);
  return String(v);
}
function Loading(){return <div className="loading"><div className="spinner"/><span>Loading...</span></div>}
function Empty({text}){return <div className="empty"><Package size={30}/><b>{text}</b></div>}
function ErrorBox({text}){return <div className="error-box"><AlertCircle size={18}/>{text}</div>}

function Farmers({refreshGlobal}) {
  const [items,setItems]=useState([]);
  const fields=[{key:"name",label:"Name"},{key:"phone",label:"Phone"},{key:"location",label:"Location"},{key:"crops",label:"Primary crop"}];
  return <DataPage title="Farmers" icon={Users} items={items} setItems={setItems} fields={fields} apiObj={{list:api.getFarmers,create:api.createFarmer,update:api.updateFarmer,remove:api.deleteFarmer}} searchPlaceholder="Search farmer, location or crop..."/>
}
function Equipment(){const [items,setItems]=useState([]);const fields=[{key:"name",label:"Name"},{key:"category",label:"Category"},{key:"price_per_day",label:"Price/day",type:"number"},{key:"location",label:"Location"}];return <DataPage title="Equipment" icon={Tractor} items={items} setItems={setItems} fields={fields} apiObj={{list:api.getEquipment,create:api.createEquipment,update:api.updateEquipment,remove:api.deleteEquipment}}/>}
function Produce(){const [items,setItems]=useState([]);const fields=[{key:"name",label:"Produce"},{key:"farmer_name",label:"Farmer"},{key:"location",label:"Location"},{key:"quantity",label:"Quantity",type:"number"},{key:"unit",label:"Unit"},{key:"price_per_unit",label:"Price/unit",type:"number"},{key:"status",label:"Status"}];return <DataPage title="Produce" icon={ShoppingBasket} items={items} setItems={setItems} fields={fields} apiObj={api.produceApi}/>}
function Restaurants(){const [items,setItems]=useState([]);const fields=[{key:"name",label:"Restaurant"},{key:"location",label:"Location"},{key:"cuisine",label:"Cuisine"},{key:"phone",label:"Phone"},{key:"demand",label:"Demand"}];return <DataPage title="Restaurants" icon={Building2} items={items} setItems={setItems} fields={fields} apiObj={api.restaurantsApi}/>}
function NGOs(){const [items,setItems]=useState([]);const fields=[{key:"name",label:"Organization"},{key:"location",label:"Location"},{key:"contact_person",label:"Contact person"},{key:"phone",label:"Phone"}];return <DataPage title="NGOs" icon={HeartHandshake} items={items} setItems={setItems} fields={fields} apiObj={api.ngosApi}/>}

function Orders(){const [items,setItems]=useState([]);const fields=[{key:"order_no",label:"Order No",required:false},{key:"produce_name",label:"Produce"},{key:"buyer",label:"Buyer"},{key:"quantity",label:"Quantity",type:"number"},{key:"unit",label:"Unit"},{key:"total",label:"Total",type:"number"},{key:"status",label:"Status"}];return <DataPage title="Orders" icon={ClipboardList} items={items} setItems={setItems} fields={fields} apiObj={api.ordersApi}/>}

function Reviews(){const [items,setItems]=useState([]);const fields=[{key:"reviewer",label:"Reviewer"},{key:"target",label:"Target"},{key:"rating",label:"Rating",type:"number"},{key:"comment",label:"Comment"}];return <DataPage title="Reviews" icon={Star} items={items} setItems={setItems} fields={fields} apiObj={api.reviewsApi}/>}

function UsersPage(){const [items,setItems]=useState([]);const fields=[{key:"name",label:"Name"},{key:"email",label:"Email",type:"email"},{key:"phone",label:"Phone"},{key:"role",label:"Role"}];return <DataPage title="Users" icon={UserRound} items={items} setItems={setItems} fields={fields} apiObj={{list:api.getUsers,create:api.createUser,update:api.updateUser,remove:api.deleteUser}}/>}

function Bookings(){
 const [items,setItems]=useState([]),[farmers,setFarmers]=useState([]),[equipment,setEquipment]=useState([]),[show,setShow]=useState(false),[form,setForm]=useState({equipment_id:"",farmer_id:"",start_date:"",end_date:""}),[error,setError]=useState("");
 async function load(){try{const [b,f,e]=await Promise.all([api.getBookings(),api.getFarmers(),api.getEquipment()]);setItems(b.bookings||[]);setFarmers(f.farmers||[]);setEquipment(e.equipment||[])}catch(e){setError(e.message)}}
 useEffect(()=>{load()},[]);
 async function submit(e){e.preventDefault();try{await api.createBooking(form);setShow(false);setForm({equipment_id:"",farmer_id:"",start_date:"",end_date:""});await load()}catch(e){setError(e.message)}}
 async function status(id,s){try{await api.updateBookingStatus(id,s);await load()}catch(e){setError(e.message)}}
 return <section><div className="page-head"><div><span className="eyebrow">BOOKING MANAGEMENT</span><h2>Equipment Bookings</h2><p>Bookings are linked to real farmers and equipment.</p></div><button className="primary" onClick={()=>setShow(true)}><Plus size={17}/> Create Booking</button></div>
 {error&&<ErrorBox text={error}/>}
 {show&&<div className="modal-backdrop"><form className="modal" onSubmit={submit}><div className="modal-head"><h3>Create booking</h3><button type="button" onClick={()=>setShow(false)}><X/></button></div><div className="form-grid">
 <label>Equipment<select required value={form.equipment_id} onChange={e=>setForm({...form,equipment_id:e.target.value})}><option value="">Select equipment</option>{equipment.filter(x=>x.available!==false).map(x=><option key={x._id} value={x._id}>{x.name} — {x.location}</option>)}</select></label>
 <label>Farmer<select required value={form.farmer_id} onChange={e=>setForm({...form,farmer_id:e.target.value})}><option value="">Select farmer</option>{farmers.map(x=><option key={x._id} value={x._id}>{x.name} — {x.location}</option>)}</select></label>
 <label>Start date<input required type="date" value={form.start_date} onChange={e=>setForm({...form,start_date:e.target.value})}/></label>
 <label>End date<input required type="date" min={form.start_date||undefined} value={form.end_date} onChange={e=>setForm({...form,end_date:e.target.value})}/></label>
 </div><div className="modal-actions"><button type="button" className="secondary" onClick={()=>setShow(false)}>Cancel</button><button className="primary">Create booking</button></div></form></div>}
 <div className="booking-list">{items.map(b=><article className="booking" key={b._id}><div className="booking-icon"><CalendarDays/></div><div className="booking-main"><div className="card-top"><div><span className="eyebrow">BOOKING</span><h3>{b.equipment_name||"Equipment"}</h3></div><span className={`status-chip ${String(b.status).toLowerCase()}`}>{b.status}</span></div><div className="facts"><div><small>Farmer</small><b>{b.farmer_name||"Unknown farmer"}</b></div><div><small>Location</small><b>{b.location||"—"}</b></div><div><small>Price/day</small><b>{b.price_per_day?String(b.price_per_day):"—"}</b></div><div><small>Dates</small><b>{b.start_date} → {b.end_date}</b></div></div><div className="card-actions">{b.status==="Pending"&&<button onClick={()=>status(b._id,"Confirmed")}><Check size={15}/> Confirm</button>}{b.status==="Confirmed"&&<button onClick={()=>status(b._id,"Completed")}><Check size={15}/> Complete</button>}{!["Cancelled","Completed"].includes(b.status)&&<button className="danger-text" onClick={()=>status(b._id,"Cancelled")}><X size={15}/> Cancel</button>}</div></div></article>)}</div>
 {!items.length&&<Empty text="No bookings found."/>}
 </section>
}

function Notifications({notifications,refreshGlobal}) {
 const [creating,setCreating]=useState(false),[form,setForm]=useState({title:"",message:"",kind:"info"});
 async function read(id){await api.markNotificationRead(id);await refreshGlobal()}
 async function all(){await api.markAllNotificationsRead();await refreshGlobal()}
 async function add(e){e.preventDefault();await api.createNotification(form);setCreating(false);setForm({title:"",message:"",kind:"info"});await refreshGlobal()}
 return <section><div className="page-head"><div><span className="eyebrow">ALERT CENTER</span><h2>Notifications</h2><p>{notifications.filter(n=>!n.read).length} unread notifications.</p></div><div className="page-actions"><button className="secondary" onClick={all}>Mark all read</button><button className="primary" onClick={()=>setCreating(true)}><Plus size={17}/> New</button></div></div>
 <div className="notice-list">{notifications.map(n=><article className={`notice-card ${n.read?"":"unread"}`} key={n._id}><div className="notice-icon"><Bell size={18}/></div><div><h3>{n.title}</h3><p>{n.message}</p><small>{n.created_at?new Date(n.created_at).toLocaleString():""}</small></div>{!n.read&&<button className="primary small" onClick={()=>read(n._id)}>Mark read</button>}</article>)}</div>
 {creating&&<FormModal title="New notification" fields={[{key:"title",label:"Title"},{key:"message",label:"Message"},{key:"kind",label:"Type",required:false}]} form={form} setForm={setForm} onClose={()=>setCreating(false)} onSubmit={add}/>}
 </section>
}


function Reports(){
 const [data,setData]=useState(null),[opt,setOpt]=useState(null),[error,setError]=useState("");
 useEffect(()=>{Promise.all([api.getReports(),api.getQueryOptimization()]).then(([r,o])=>{setData(r);setOpt(o)}).catch(e=>setError(e.message))},[]);
 if(error) return <section><ErrorBox text={error}/></section>;
 if(!data) return <section><Loading/></section>;
 return <section><div className="page-head"><div><span className="eyebrow">DBMS REPORTS</span><h2>Aggregation Reports</h2><p>MongoDB aggregation pipelines for management reporting and top-N analysis.</p></div></div>
 <div className="stats-grid"><div className="stat-card"><small>Order status groups</small><strong>{data.order_status.length}</strong></div><div className="stat-card"><small>Top farmers</small><strong>{data.top_farmers.length}</strong></div><div className="stat-card"><small>Produce demand rows</small><strong>{data.produce_demand.length}</strong></div></div>
 <div className="table-card"><h3>Order Status Summary</h3><table><thead><tr><th>Status</th><th>Orders</th><th>Revenue</th></tr></thead><tbody>{data.order_status.map((r,i)=><tr key={i}><td>{r._id||"Unknown"}</td><td>{r.orders}</td><td>{r.revenue}</td></tr>)}</tbody></table></div>
 <div className="table-card"><h3>Top Farmers by Quantity Sold</h3><table><thead><tr><th>Farmer</th><th>Orders</th><th>Quantity (kg)</th><th>Revenue</th></tr></thead><tbody>{data.top_farmers.map((r,i)=><tr key={i}><td>{r.farmer}</td><td>{r.orders}</td><td>{r.quantity_kg}</td><td>{r.revenue}</td></tr>)}</tbody></table></div>
 <div className="table-card"><h3>Produce Demand</h3><table><thead><tr><th>Produce ID</th><th>Orders</th><th>Quantity (kg)</th><th>Revenue</th></tr></thead><tbody>{data.produce_demand.map((r,i)=><tr key={i}><td>{r._id||"Unknown"}</td><td>{r.orders}</td><td>{r.quantity_kg}</td><td>{r.revenue}</td></tr>)}</tbody></table></div>
 <div className="table-card"><h3>Query Optimization</h3><p>Indexes created for frequently queried fields.</p><pre>{JSON.stringify(opt?.indexes||{},null,2)}</pre></div>
 </section>
}

function AISearch(){
 const [q,setQ]=useState(""),[data,setData]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState("");
 async function run(e){e?.preventDefault();setLoading(true);setError("");try{setData(await api.aiSearch(q))}catch(err){setError(err.message)}finally{setLoading(false)}}
 return <section><div className="page-head"><div><span className="eyebrow">AI-ASSISTED SEARCH</span><h2>Natural Language Search</h2><p>Type a simple business question; it is mapped to a predefined MongoDB query or aggregation pipeline.</p></div></div>
 <form className="search-bar" onSubmit={run}><Search size={18}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Try: top farmers by quantity"/><button className="primary">Search</button></form>
 <div className="suggestions"><button onClick={()=>{setQ("cancelled orders");}}>Cancelled orders</button><button onClick={()=>{setQ("top farmers by quantity");}}>Top farmers by quantity</button><button onClick={()=>{setQ("produce demand");}}>Produce demand</button></div>
 {loading&&<Loading/>}{error&&<ErrorBox text={error}/>} {data&&<div className="table-card"><h3>{data.title}</h3><p>{data.explanation}</p>{data.rows.length?<div className="table-wrap"><table><thead><tr>{Object.keys(data.rows[0]).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{data.rows.map((r,i)=><tr key={i}>{Object.values(r).map((v,j)=><td key={j}>{formatValue(v)}</td>)}</tr>)}</tbody></table></div>:<Empty text="No mapped results."/>}</div>}
 </section>
}

function renderPage(page,ctx){
 switch(page){
  case "Dashboard": return <DashboardPage key={page} {...ctx}/>;
  case "Reports": return <Reports key={page}/>;
  case "AI Search": return <AISearch key={page}/>;
  case "Farmers": return <Farmers key={page} refreshGlobal={ctx.refreshGlobal}/>;
  case "Equipment": return <Equipment key={page}/>;
  case "Bookings": return <Bookings key={page}/>;
  case "Produce": return <Produce key={page}/>;
  case "Orders": return <Orders key={page}/>;
  case "Restaurants": return <Restaurants key={page}/>;
  case "NGOs": return <NGOs key={page}/>;
  case "Reviews": return <Reviews key={page}/>;
  case "Notifications": return <Notifications key={page} notifications={ctx.notifications} refreshGlobal={ctx.refreshGlobal}/>;
  case "Users": return <UsersPage key={page}/>;
  default: return null;
 }
}

export default App;
