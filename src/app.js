{
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const WA=document.body.dataset.wa||'';

/* mobile menu */
const mb=$('.menu-btn'),nav=$('.nav');
if(mb&&nav)mb.addEventListener('click',()=>{const o=nav.classList.toggle('open');mb.setAttribute('aria-expanded',o)});

/* reveal on scroll */
const io=('IntersectionObserver' in window)?new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{rootMargin:'0px 0px -8% 0px'}):null;
$$('.reveal').forEach(el=>io?io.observe(el):el.classList.add('in'));

/* photo fallback: if a remote photo fails, show the drawn facade underneath */
$$('img[data-fallback]').forEach(img=>{const kill=()=>img.remove();img.addEventListener('error',kill);if(img.complete&&!img.naturalWidth)kill()});

/* home search -> listings */
const hs=$('#home-search');
if(hs){
  let stage='all';
  $$('.tab',hs.parentElement).forEach(t=>t.addEventListener('click',()=>{stage=t.dataset.stage;$$('.tab',hs.parentElement).forEach(x=>x.setAttribute('aria-selected',x===t))}));
  hs.addEventListener('submit',e=>{e.preventDefault();const f=Object.fromEntries(new FormData(hs));f.stage=stage;
    try{sessionStorage.setItem('arte-filter',JSON.stringify(f))}catch(_){}
    location.href='listings.html?'+new URLSearchParams(f).toString()});
}

/* listings filter */
const lf=$('#filter');
if(lf){
  const cards=$$('[data-listing]'),count=$('#count'),empty=$('#empty');
  const tabs=$$('.tab',lf.parentElement);
  let stage='all';
  const setStage=s=>{stage=s;tabs.forEach(t=>t.setAttribute('aria-selected',t.dataset.stage===s))};
  // read initial filters from query, hash or session
  let init={};
  try{init=Object.fromEntries(new URLSearchParams(location.search))}catch(_){}
  if(!Object.keys(init).length){try{init=JSON.parse(sessionStorage.getItem('arte-filter')||'{}')}catch(_){}}
  const h=location.hash.slice(1);if(['sale','rent','offplan','ready','signature'].includes(h))init.stage=h;
  for(const[k,v]of Object.entries(init)){const el=lf.elements[k];if(el)el.value=v}
  setStage(init.stage||'all');
  const apply=()=>{
    const f=Object.fromEntries(new FormData(lf));
    const min=+f.min||0,max=+f.max||Infinity,beds=f.beds;let n=0;
    cards.forEach(c=>{const d=c.dataset,p=+d.price||0;
      const ok=(stage==='all'||(stage==='sale'&&d.status==='sale')||(stage==='rent'&&d.status==='rent')||(stage==='offplan'&&d.stage==='offplan')||(stage==='signature'&&d.sig==='1'))
        &&(!f.area||d.area===f.area)&&(!f.type||d.type===f.type)
        &&(!beds||(d.beds!==''&&(beds==='4'?+d.bedsmax>=4:(+d.beds<=+beds&&+d.bedsmax>=+beds))))
        &&(!p||(p>=min&&p<=max))&&(p||(!f.min&&!f.max));
      c.hidden=!ok;if(ok)n++});
    count.textContent=n+(n===1?' property':' properties');empty.hidden=n>0;
    try{sessionStorage.setItem('arte-filter',JSON.stringify({...f,stage}))}catch(_){}
  };
  tabs.forEach(t=>t.addEventListener('click',()=>{setStage(t.dataset.stage);apply()}));
  lf.addEventListener('input',apply);lf.addEventListener('submit',e=>{e.preventDefault();apply()});
  $('#clear').addEventListener('click',()=>{lf.reset();setStage('all');apply()});
  apply();
}

/* lead forms: Netlify Forms when deployed, WhatsApp as the fallback */
$$('form[data-netlify]').forEach(form=>{
  const note=$('.note',form)||form.nextElementSibling;
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    if(form.elements['bot-field']&&form.elements['bot-field'].value)return;
    const btn=$('button[type=submit]',form);btn.disabled=true;const label=btn.textContent;btn.textContent='Sending…';
    const data=new FormData(form);
    const text=[...data.entries()].filter(([k,v])=>v&&!['form-name','bot-field'].includes(k)).map(([k,v])=>k.replace(/-/g,' ')+': '+v).join('\n');
    const wa='https://wa.me/'+WA+'?text='+encodeURIComponent('Hello ARTÉ Properties\n'+text);
    let ok=false;
    try{const r=await fetch('/',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(data).toString()});ok=r.ok&&!/claude|localhost|127\.0\.0\.1/.test(location.hostname)}catch(_){}
    btn.disabled=false;btn.textContent=label;
    note.className='note '+(ok?'ok':'err');
    note.innerHTML=ok?'Thank you. A member of the team will be in touch shortly.'
      :'We could not send this form from here. <a href="'+wa+'" target="_blank" rel="noopener">Send it on WhatsApp instead</a> or call <a href="tel:'+document.body.dataset.tel+'">'+document.body.dataset.phone+'</a>.';
    if(ok){window.arteEvent&&arteEvent('generate_lead',{form_name:form.getAttribute('name'),page:location.pathname});form.reset();document.querySelectorAll('input[data-utm]').forEach(i=>{try{const a=JSON.parse(sessionStorage.getItem('arte-attr')||'{}');if(a[i.name])i.value=a[i.name]}catch(_){}})}
  });
});
}
{
/* photo carousel on property pages */
document.querySelectorAll('[data-carousel]').forEach(c=>{
  const t=c.querySelector('.track'),n=c.querySelector('.count b'),slides=[...t.children];
  const go=d=>{const i=Math.round(t.scrollLeft/t.clientWidth);const j=Math.max(0,Math.min(slides.length-1,i+d));t.scrollTo({left:j*t.clientWidth,behavior:'smooth'})};
  c.querySelector('.prev').addEventListener('click',()=>go(-1));c.querySelector('.next').addEventListener('click',()=>go(1));
  t.addEventListener('scroll',()=>{n.textContent=Math.round(t.scrollLeft/t.clientWidth)+1},{passive:true});
  c.tabIndex=0;c.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')go(-1);if(e.key==='ArrowRight')go(1)});
});
}
{
/* attribution: keep the first ad/link details for this visit and copy them into every lead form */
const KEYS=['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid'];
let a={};try{a=JSON.parse(sessionStorage.getItem('arte-attr')||'{}')}catch(_){}
const q=new URLSearchParams(location.search);
if(KEYS.some(k=>q.get(k))){a={};KEYS.forEach(k=>{if(q.get(k))a[k]=q.get(k)});a.landing_page=location.pathname}
if(!a.landing_page)a.landing_page=location.pathname;
try{sessionStorage.setItem('arte-attr',JSON.stringify(a))}catch(_){}
document.querySelectorAll('input[data-utm]').forEach(i=>{if(a[i.name])i.value=a[i.name]});

/* tracking: only when IDs are set in data/site.json, and only after the visitor accepts cookies */
const T=window.ARTE_T;
window.arteEvent=(name,params)=>{if(!T)return;try{dataLayer.push(Object.assign({event:name},params||{}))}catch(_){}
  if(window.__arteOn){
    if(T.ga4_id&&window.gtag)gtag('event',name,params||{});
    if(name==='generate_lead'&&T.ads_id&&T.ads_lead_label&&window.gtag)gtag('event','conversion',{send_to:T.ads_id+'/'+T.ads_lead_label});
    if(window.fbq)fbq('track',name==='generate_lead'?'Lead':'Contact',params||{});
  }};
if(T){
  const load=src=>{const s=document.createElement('script');s.async=true;s.src=src;document.head.appendChild(s)};
  const on=()=>{if(window.__arteOn)return;window.__arteOn=true;
    gtag('consent','update',{ad_storage:'granted',analytics_storage:'granted',ad_user_data:'granted',ad_personalization:'granted'});
    if(T.gtm_id){dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});load('https://www.googletagmanager.com/gtm.js?id='+T.gtm_id)}
    const g=T.ga4_id||T.ads_id;
    if(g){load('https://www.googletagmanager.com/gtag/js?id='+g);gtag('js',new Date());if(T.ga4_id)gtag('config',T.ga4_id);if(T.ads_id)gtag('config',T.ads_id)}
    if(T.meta_pixel_id){!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init',T.meta_pixel_id);fbq('track','PageView')}
  };
  let choice=null;try{choice=localStorage.getItem('arte-consent')}catch(_){}
  const save=v=>{try{localStorage.setItem('arte-consent',v)}catch(_){}};
  const banner=()=>{if(document.querySelector('.cookie'))return;
    const d=document.createElement('div');d.className='cookie';d.setAttribute('role','dialog');d.setAttribute('aria-label','Cookie choice');
    d.innerHTML='<p>We use cookies from Google and Meta to see how the site is used and which adverts work. Nothing loads unless you accept. <a href="privacy.html">Privacy notice</a></p><div><button class="btn ghost sm" data-c="no">Decline</button><button class="btn sm" data-c="yes">Accept</button></div>';
    d.addEventListener('click',ev=>{const c=ev.target.dataset&&ev.target.dataset.c;if(!c)return;
      if(c==='yes'){save('granted');on()}else{const was=window.__arteOn;save('denied');if(was)location.reload()}d.remove()});
    document.body.appendChild(d)};
  if(choice==='granted')on();else if(choice!=='denied')banner();
  document.querySelectorAll('[data-cookie-settings]').forEach(l=>l.addEventListener('click',ev=>{ev.preventDefault();banner()}));
}
/* click events */
document.addEventListener('click',ev=>{const l=ev.target.closest&&ev.target.closest('a[href]');if(!l)return;
  const h=l.getAttribute('href');
  if(h.startsWith('https://wa.me/'))arteEvent('whatsapp_click',{page:location.pathname});
  else if(h.startsWith('tel:'))arteEvent('phone_click',{page:location.pathname});
});
}
