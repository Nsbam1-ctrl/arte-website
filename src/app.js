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
    if(ok)form.reset();
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
