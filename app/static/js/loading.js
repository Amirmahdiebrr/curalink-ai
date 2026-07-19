const texts=[

"درحال دریافت فایل ...",

"استخراج متن آزمایش ...",

"بررسی مقادیر ...",

"تحلیل توسط هوش مصنوعی ...",

"تولید گزارش ..."

];

let i=0;

setInterval(()=>{

const el=document.getElementById("loading-text");

if(el){

el.innerHTML=texts[i];

i++;

if(i>=texts.length){

i=0;

}

}

},1800);