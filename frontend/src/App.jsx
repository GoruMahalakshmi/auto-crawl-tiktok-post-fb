import { useState, useEffect } from 'react';
import { 
  RefreshCw, Copy, Radio, Share2, Play, CloudDownload, 
  CircleCheck, CircleX, Clock, Terminal, Bot, Activity, ChevronRight, PlusCircle, LogOut, KeyRound, ExternalLink, Zap, Database, Flag
} from 'lucide-react';

const API_URL = "/api";

function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [videos, setVideos] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [formData, setFormData] = useState({ name: "", source_url: "", auto_post: false, target_page_id: "", schedule_interval: 0 });
  const [fbPages, setFbPages] = useState([]);
  const [fbForm, setFbForm] = useState({ page_id: "", page_name: "", long_lived_access_token: "" });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [stats, setStats] = useState({ total: 0, pending: 0, ready: 0, posted: 0, failed: 0 });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');

  const authFetch = async (url, options = {}) => {
    const headers = { ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      setToken(null);
      localStorage.removeItem('token');
      throw new Error('Unauthorized');
    }
    return res;
  };

  const fetchDashboard = async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      const campRes = await authFetch(`${API_URL}/campaigns/`);
      setCampaigns(await campRes.json());
      
      const statRes = await authFetch(`${API_URL}/campaigns/stats`);
      setStats(await statRes.json());

      const vidRes = await authFetch(`${API_URL}/campaigns/videos?page=${page}&limit=10`);
      const vidData = await vidRes.json();
      setVideos(vidData.videos);
      setTotalPages(vidData.pages);

      const fbRes = await authFetch(`${API_URL}/facebook/config`);
      const fbData = await fbRes.json();
      setFbPages(fbData);

      const logRes = await authFetch(`${API_URL}/webhooks/logs`);
      setInteractions(await logRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 5000);
    return () => clearInterval(interval);
  }, [token, page]);

  // Tự động chọn Fanpage đầu tiên nếu chưa chọn
  useEffect(() => {
    if (fbPages.length > 0 && !formData.target_page_id) {
      setFormData(f => ({ ...f, target_page_id: fbPages[0].page_id }));
    }
  }, [fbPages]);

  const handleCampaignSubmit = async (e) => {
    e.preventDefault();
    if (!formData.target_page_id && fbPages.length > 0) {
      alert("Vui lòng chọn Fanpage đích!");
      return;
    }
    try {
      const res = await authFetch(`${API_URL}/campaigns/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setFormData({ ...formData, name: "", source_url: "", auto_post: false, schedule_interval: 0 });
        fetchDashboard();
      }
    } catch(e) {
      alert("Lỗi kết nối Server");
    }
  };

  const handleFbSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await authFetch(`${API_URL}/facebook/config`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fbForm)
      });
      if (res.ok) {
        setFbForm({ page_id: "", page_name: "", long_lived_access_token: "" }); 
        fetchDashboard();
      }
    } catch(e) {
      alert("Lỗi kết nối Server");
    }
  };

  const handlePrioritize = async (videoId) => {
    try {
      const res = await authFetch(`${API_URL}/campaigns/videos/${videoId}/priority`, { method: "POST" });
      if (res.ok) {
        fetchDashboard();
      }
    } catch(e) {
      alert("Lỗi kết nối Server");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const formatRelTime = (isoStr) => {
    if (!isoStr) return "N/A";
    const date = new Date(isoStr + 'Z');
    const diff = Math.floor((date - new Date()) / 60000);
    if (diff < 0) return "Sắp đăng...";
    if (diff < 60) return `${diff} phút nữa`;
    const hours = Math.floor(diff / 60);
    if (hours < 24) return `${hours} giờ nữa`;
    return `${Math.floor(hours / 24)} ngày nữa`;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: loginPass })
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        setLoginError('');
      } else {
        setLoginError('Mật khẩu không chính xác!');
      }
    } catch(e) {
      setLoginError('Lỗi kết nối Server');
    }
  };

  const handleLogout = () => {
    setToken(null);
    setLoginPass('');
    localStorage.removeItem('token');
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-[#012456] flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-sm premium-card p-8 flex flex-col items-center">
          <div className="w-16 h-16 rounded-2xl bg-black/20 border border-white/10 flex items-center justify-center mb-6 shadow-lg">
            <KeyRound className="w-8 h-8 text-sky-400" />
          </div>
          <h1 className="text-xl font-bold text-white mb-2">Social Automation</h1>
          <p className="text-sm text-blue-300/70 mb-8 text-center">Vui lòng nhập mật khẩu quản trị để truy cập hệ thống.</p>
          
          <form onSubmit={handleLogin} className="w-full space-y-4">
            <div>
              <input type="password" required className="premium-input w-full px-4 py-3 text-sm text-center tracking-widest" 
                     placeholder="••••••••" value={loginPass} onChange={e => setLoginPass(e.target.value)} />
            </div>
            {loginError && <p className="text-xs text-rose-400 text-center bg-rose-500/10 py-2 rounded border border-rose-500/20">{loginError}</p>}
            <button type="submit" className="premium-button w-full py-3 text-sm flex items-center justify-center gap-2">
              Tiến vào Hệ thống <ChevronRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#012456] text-blue-100 font-sans selection:bg-sky-500/30 overflow-x-hidden pb-16">
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-400/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 relative z-10">
        
        {/* HEADER */}
        <header className="flex flex-col md:flex-row items-center justify-between mb-12 gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-black/20 border border-white/10 flex items-center justify-center shadow-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Hệ thống SocialAI (Đa Fanpage)</h1>
              <p className="text-sm text-blue-300/70 mt-1">Công cụ Cào TikTok & Đăng Facebook Hàng Loạt</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={fetchDashboard} className="flex items-center gap-2 px-4 py-2 bg-black/20 border border-white/10 hover:bg-black/30 hover:border-white/20 text-white text-sm font-medium rounded-lg transition-all">
              <RefreshCw className={`w-4 h-4 text-blue-300 ${isRefreshing ? 'animate-spin text-white' : ''}`} /> Làm mới Dữ liệu
            </button>
            <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 text-rose-300 text-sm font-medium rounded-lg transition-all">
              <LogOut className="w-4 h-4" /> Thoát
            </button>
          </div>
        </header>

        {/* STATS CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <div className="premium-card p-4 flex flex-col items-center justify-center text-center group border-blue-500/20">
            <div className="text-2xl font-bold text-white mb-1 group-hover:scale-110 transition-transform">{stats.total}</div>
            <div className="text-[10px] uppercase tracking-widest text-blue-300/60 font-semibold">Tổng Video</div>
          </div>
          <div className="premium-card p-4 flex flex-col items-center justify-center text-center group border-amber-500/20">
            <div className="text-2xl font-bold text-amber-400 mb-1 group-hover:scale-110 transition-transform">{stats.ready + stats.pending}</div>
            <div className="text-[10px] uppercase tracking-widest text-amber-300/60 font-semibold">Đang Chờ Đăng</div>
          </div>
          <div className="premium-card p-4 flex flex-col items-center justify-center text-center group border-emerald-500/20">
            <div className="text-2xl font-bold text-emerald-400 mb-1 group-hover:scale-110 transition-transform">{stats.posted}</div>
            <div className="text-[10px] uppercase tracking-widest text-emerald-300/60 font-semibold">Đã Lên Sóng</div>
          </div>
          <div className="premium-card p-4 flex flex-col items-center justify-center text-center group border-rose-500/20">
            <div className="text-2xl font-bold text-rose-400 mb-1 group-hover:scale-110 transition-transform">{stats.failed}</div>
            <div className="text-[10px] uppercase tracking-widest text-rose-300/60 font-semibold">Đăng Thất Bại</div>
          </div>
        </div>

        {/* QUEUE TIMELINE OVERVIEW */}
        {(stats.next_publish || stats.last_publish) && (
          <div className="bg-sky-500/5 border border-sky-500/10 rounded-xl p-4 mb-10 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-400 animate-pulse" />
              </div>
              <div className="text-left">
                <div className="text-[10px] uppercase font-bold text-amber-300/60 tracking-wider">Video Tiếp theo</div>
                <div className="text-sm font-semibold text-white">
                  {stats.next_publish ? `${new Date(stats.next_publish + 'Z').toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})} (${formatRelTime(stats.next_publish)})` : "N/A"}
                </div>
              </div>
            </div>
            
            <div className="h-px w-full md:h-8 md:w-px bg-white/10 hidden md:block" />

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                <Flag className="w-5 h-5 text-sky-400" />
              </div>
              <div className="text-left">
                <div className="text-[10px] uppercase font-bold text-sky-300/60 tracking-wider">Hoàn thành Hàng chờ</div>
                <div className="text-sm font-semibold text-white">
                  {stats.last_publish ? `${new Date(stats.last_publish + 'Z').toLocaleString('vi-VN', {day: '2-digit', month: '2-digit', hour: '2-digit', minute:'2-digit'})}` : "N/A"}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TOP SECTION: CONFIG & WEBHOOK */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          
          {/* Facebook Config Card (MULTI-PAGE) */}
          <div className="premium-card p-6 flex flex-col">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Share2 className="w-4 h-4 text-sky-400" /> Fanpage Đang Hoạt Động
              </h2>
              <span className="text-xs font-medium bg-black/30 px-2.5 py-1 rounded-full text-blue-300 border border-white/5">
                {fbPages.length} Đã Kết Nối
              </span>
            </div>
            
            {/* List of Connected Pages */}
            <div className="flex-1 mb-6 space-y-2 max-h-40 overflow-y-auto pr-2">
              {fbPages.length === 0 ? (
                <div className="text-center text-sm text-blue-300/50 py-4 italic">Chưa có Fanpage nào được kết nối. Hãy thêm ở bên dưới.</div>
              ) : (
                fbPages.map(page => (
                  <div key={page.page_id} className="flex justify-between items-center bg-black/20 border border-white/10 p-3 rounded-lg">
                    <div>
                      <div className="font-semibold text-white text-sm">{page.page_name}</div>
                      <div className="font-mono text-xs text-blue-300/60 mt-0.5">ID: {page.page_id}</div>
                    </div>
                    <span className="flex items-center gap-1.5 px-2 py-1 text-[10px] uppercase font-bold bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Hoạt động
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Add New Page Form */}
            <div className="pt-4 border-t border-white/10">
              <h3 className="text-xs font-semibold text-sky-300 mb-3 flex items-center gap-1.5 uppercase tracking-wider">
                <PlusCircle className="w-3.5 h-3.5" /> Thêm Fanpage Mới
              </h3>
              <form onSubmit={handleFbSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input required type="text" className="premium-input w-full px-3 py-2 text-xs placeholder:text-blue-200/30" 
                         value={fbForm.page_id} onChange={e => setFbForm({...fbForm, page_id: e.target.value})} placeholder="ID Fanpage (1076...)" />
                  <input required type="text" className="premium-input w-full px-3 py-2 text-xs placeholder:text-blue-200/30" 
                         value={fbForm.page_name} onChange={e => setFbForm({...fbForm, page_name: e.target.value})} placeholder="Tên Fanpage" />
                </div>
                <input required type="text" placeholder="Mã Access Token (Hoặc Link Webhook n8n/Make)" 
                       className="premium-input w-full px-3 py-2 text-xs placeholder:text-blue-200/30" 
                       value={fbForm.long_lived_access_token} onChange={e => setFbForm({...fbForm, long_lived_access_token: e.target.value})} />
                <button type="submit" className="w-full bg-sky-500/20 hover:bg-sky-500/30 text-sky-100 font-medium py-2 rounded-md text-xs transition-all border border-sky-400/30">
                  Kết nối Fanpage
                </button>
              </form>
            </div>
          </div>

          {/* Webhook Tunnel Card */}
          <div className="premium-card p-6 flex flex-col">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Radio className="w-4 h-4 text-amber-400" /> Cổng Nhận Webhook
              </h2>
            </div>
            
            <div className="space-y-5 flex-1">
              <p className="text-sm text-blue-100/70 leading-relaxed">
                Kết nối tương tác thời gian thực của Facebook tới máy chủ qua Cloudflare Tunnel. Hãy sử dụng các thông tin bên dưới để cấu hình trong App Dashboard của Meta. Hoạt động chung cho mọi Fanpage.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-blue-200/70 mb-2">URL Gọi lại (Callback)</label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-black/30 border border-white/10 rounded-lg p-2.5 overflow-hidden">
                      <code className="text-xs text-blue-200 font-mono flex items-center gap-2 whitespace-nowrap overflow-x-auto">
                        https://civic-marking-speaking-plot.trycloudflare.com/webhooks/fb
                      </code>
                    </div>
                    <button onClick={() => copyToClipboard("https://civic-marking-speaking-plot.trycloudflare.com/webhooks/fb")} 
                            className="p-2.5 rounded-lg bg-black/20 hover:bg-white/10 border border-white/10 transition-colors text-blue-300 hover:text-white" title="Copy URL">
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-blue-200/70 mb-2">Mã Xác thực (Verify Token)</label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-black/30 border border-white/10 rounded-lg p-2.5">
                      <code className="text-xs text-amber-300 font-mono">social_auto_2026</code>
                    </div>
                    <button onClick={() => copyToClipboard("social_auto_2026")} 
                            className="p-2.5 rounded-lg bg-black/20 hover:bg-white/10 border border-white/10 transition-colors text-blue-300 hover:text-white" title="Copy Token">
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* CRAWL CAMPAIGN INPUT */}
        <div className="premium-card p-6 mb-6 relative overflow-hidden">
          <div className="flex items-center mb-6 pb-4 border-b border-white/10">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <CloudDownload className="w-4 h-4 text-sky-400" /> Khởi tạo Luồng Cào Video
            </h2>
          </div>
          
          <form onSubmit={handleCampaignSubmit} className="flex flex-col md:flex-row gap-4 items-end">
            <div className="w-full md:w-1/5">
              <label className="block text-xs font-medium text-blue-200/70 mb-1.5">Fanpage Đích</label>
              <select required className="premium-input w-full px-3 py-2.5 text-sm cursor-pointer"
                      value={formData.target_page_id} onChange={e => setFormData({...formData, target_page_id: e.target.value})}
                      disabled={fbPages.length === 0}>
                {fbPages.length === 0 && <option value="">Chưa có Fanpage</option>}
                {fbPages.map(p => <option key={p.page_id} value={p.page_id} style={{color: '#012456'}}>{p.page_name}</option>)}
              </select>
            </div>
            <div className="w-full md:w-[25%]">
              <label className="block text-xs font-medium text-blue-200/70 mb-1.5">Tên Chiến Dịch</label>
              <input required type="text" className="premium-input w-full px-3 py-2.5 text-sm placeholder:text-blue-200/30" 
                     value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="VD: Giải trí Mỗi ngày" />
            </div>
            <div className="w-full md:w-[25%]">
              <label className="block text-xs font-medium text-blue-200/70 mb-1.5">Link Kênh TikTok Nguồn</label>
              <input required type="url" className="premium-input w-full px-3 py-2.5 text-sm placeholder:text-blue-200/30" 
                     value={formData.source_url} onChange={e => setFormData({...formData, source_url: e.target.value})} placeholder="https://www.tiktok.com/@..." />
            </div>
            
            <div className="w-full md:w-[15%]">
              <label className="block text-xs font-medium text-blue-200/70 mb-1.5">Tần suất (Phút)</label>
              <input required type="number" min="0" className="premium-input w-full px-3 py-2.5 text-sm placeholder:text-blue-200/30" 
                     value={formData.schedule_interval} onChange={e => setFormData({...formData, schedule_interval: parseInt(e.target.value) || 0})} placeholder="VD: 30" />
            </div>
            
            <div className="w-full md:flex-1 pb-1 px-4 flex justify-center">
              <label className="flex items-center gap-2 cursor-pointer group">
                <div className="relative flex items-center">
                  <input type="checkbox" className="sr-only peer" checked={formData.auto_post} onChange={e => setFormData({...formData, auto_post: e.target.checked})} />
                  <div className="w-9 h-5 bg-black/40 border border-white/20 rounded-full peer peer-checked:bg-sky-500 peer-checked:border-sky-400 transition-all after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-blue-300 peer-checked:after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
                </div>
                <span className="text-xs font-medium text-blue-200 group-hover:text-white transition-colors">Tự động Đăng</span>
              </label>
            </div>

            <button type="submit" disabled={fbPages.length === 0} className="premium-button w-full md:w-auto px-6 py-2.5 text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <Play className="w-4 h-4" /> Bắt đầu Cào
            </button>
          </form>
          {fbPages.length === 0 && (
             <div className="absolute inset-0 bg-[#012456]/80 backdrop-blur-sm flex items-center justify-center rounded-xl z-20">
               <span className="text-amber-300 font-medium flex items-center gap-2">
                 <Radio className="w-5 h-5 animate-pulse" /> Vui lòng kết nối ít nhất một Fanpage trước khi chạy
               </span>
             </div>
          )}
        </div>

        {/* TABLES GRID */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          
          {/* MEDIA PIPELINE */}
          <div className="premium-card flex flex-col overflow-hidden h-[500px]">
            <div className="p-5 border-b border-white/10 bg-black/10">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-blue-300" /> Tiến trình Xử lý Video
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-[#012456]/90 backdrop-blur-sm border-b border-white/10">
                  <tr>
                    <th className="px-5 py-3 text-xs font-semibold text-blue-200/70">ID Nội dung & Page Đích</th>
                    <th className="px-5 py-3 text-xs font-semibold text-blue-200/70">Trạng thái & AI Xử lý</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {videos.length === 0 && (
                    <tr><td colSpan="2" className="px-5 py-12 text-center text-blue-300/50 text-sm">Chưa có video nào trong hệ thống.</td></tr>
                  )}
                  {videos.map(v => {
                    const campaign = campaigns.find(c => c.id === v.campaign_id);
                    const targetPage = campaign ? fbPages.find(p => p.page_id === campaign.target_page_id) : null;
                    return (
                      <tr key={v.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-5 py-4 align-top w-1/2">
                          <div className="font-mono text-xs text-white mb-1.5">{v.original_id}</div>
                          {targetPage && (
                            <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-sky-500/10 text-sky-300 border border-sky-500/20 mb-2">
                              ĐÍCH: {targetPage.page_name}
                            </div>
                          )}
                          <div className="text-xs text-blue-200/70 line-clamp-2" title={v.original_caption}>{v.original_caption}</div>
                        </td>
                        <td className="px-5 py-4 align-top w-1/2">
                          <div className="mb-3">
                            {v.status === 'ready' ? (
                              <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex w-fit items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium bg-black/30 border border-white/10 text-amber-300">
                                    <Clock className="w-3 h-3" /> Đang xếp hàng
                                  </span>
                                  {v.publish_time && new Date(v.publish_time + 'Z') > new Date() && (
                                    <button 
                                      onClick={() => handlePrioritize(v.id)}
                                      title="Ưu tiên đăng ngay"
                                      className="p-1.5 hover:bg-yellow-400/20 rounded text-yellow-400 transition-all hover:scale-110 active:scale-95 border border-yellow-400/30"
                                    >
                                      <Zap size={14} fill="currentColor" />
                                    </button>
                                  )}
                                </div>
                                {v.publish_time && (
                                  <span className="text-[10px] text-blue-200/60 font-mono">
                                    Lên sóng: {new Date(v.publish_time + 'Z').toLocaleString('vi-VN')}
                                  </span>
                                )}
                              </div>
                            ) : v.status === 'posted' ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">
                                <CircleCheck className="w-3 h-3" /> Đã Lên Sóng
                              </span>
                            ) : v.status === 'failed' ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium bg-rose-500/20 border border-rose-500/30 text-rose-300">
                                <CircleX className="w-3 h-3" /> Đăng Thất bại
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium bg-sky-500/20 border border-sky-500/30 text-sky-300">
                                <RefreshCw className="w-3 h-3 animate-spin" /> Đang Cào & Xử lý
                              </span>
                            )}
                          </div>
                          {v.ai_caption && (
                            <div className="text-xs text-blue-200 whitespace-pre-wrap">{v.ai_caption}</div>
                          )}
                          {v.fb_post_id && (
                            <div className="mt-2 flex items-center gap-1">
                              <a 
                                href={`https://www.facebook.com/reel/${v.fb_post_id}/`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono text-sky-300 bg-sky-500/10 border border-sky-500/20 hover:bg-sky-500/20 hover:text-white transition-all group"
                                title="Xem trên Facebook"
                              >
                                <ExternalLink className="w-3 h-3 group-hover:scale-110 transition-transform" /> {v.fb_post_id}
                              </a>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* PAGINATION CONTROLS */}
            <div className="p-4 border-t border-white/10 bg-black/10 flex items-center justify-between">
              <p className="text-[10px] text-blue-300/50 uppercase font-semibold">
                Trang {page} / {totalPages}
              </p>
              <div className="flex gap-2">
                <button 
                  disabled={page <= 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  className="px-3 py-1 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Trước
                </button>
                <button 
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  className="px-3 py-1 rounded bg-white/5 border border-white/10 text-xs hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Sau
                </button>
              </div>
            </div>
          </div>

          {/* WEBHOOK ACTIVITY */}
          <div className="premium-card flex flex-col overflow-hidden h-[500px]">
            <div className="p-5 border-b border-white/10 bg-black/10">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Bot className="w-4 h-4 text-emerald-400" /> Nhật ký Hoạt động Máy chủ
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-[#012456]/90 backdrop-blur-sm border-b border-white/10">
                  <tr>
                    <th className="px-5 py-3 text-xs font-semibold text-blue-200/70">Khách hàng Bình luận</th>
                    <th className="px-5 py-3 text-xs font-semibold text-blue-200/70">AI Tự động Trả lời</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {interactions.length === 0 && (
                    <tr><td colSpan="2" className="px-5 py-12 text-center text-blue-300/50 text-sm">Đang chờ sự kiện tương tác từ Facebook...</td></tr>
                  )}
                  {interactions.map(log => {
                    const targetPage = fbPages.find(p => p.page_id === log.page_id);
                    return (
                      <tr key={log.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-5 py-4 align-top w-1/2">
                          <div className="font-mono text-[10px] text-blue-300/50 mb-1 flex items-center gap-1">
                            KHÁCH: {log.user_id} 
                            {targetPage && <><ChevronRight className="w-3 h-3"/> TỚI: <span className="text-sky-300">{targetPage.page_name}</span></>}
                          </div>
                          <div className="text-sm text-blue-100 bg-black/20 px-3 py-2 rounded-lg border border-white/5">
                            {log.user_message}
                          </div>
                        </td>
                        <td className="px-5 py-4 align-top w-1/2">
                          <div className="mb-2">
                            {log.status === 'pending' ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                <RefreshCw className="w-3 h-3 animate-spin"/> Đang Suy nghĩ
                              </span>
                            ) : log.status === 'replied' ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                <CircleCheck className="w-3 h-3" /> Đã Trả lời
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                <CircleX className="w-3 h-3" /> Bị Lỗi
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-blue-200/80 leading-relaxed border-l-2 border-white/10 pl-3">
                            {log.ai_reply || <span className="opacity-50">Đang khởi tạo câu trả lời...</span>}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

export default App;
