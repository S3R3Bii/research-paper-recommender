'use strict';
const form=document.querySelector('#search-form'),query=document.querySelector('#query'),status=document.querySelector('#status'),results=document.querySelector('#results'),submit=document.querySelector('#submit');
function element(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
async function search(){
 if(!query.value.trim()){query.focus();return;}
 submit.disabled=true;status.textContent='Looking through local titles…';results.replaceChildren();
 try{
  const year=document.querySelector('#before-year').value;const body={query:query.value};if(year)body.before_year=Number(year);
  const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw new Error(data.error||'Search unavailable');
  if(data.abstained){const box=element('div',undefined,'empty');box.append(element('h3','No strong title match.'),element('p','Try a more specific research title or a known DOI. Abstention reflects this small catalog and lexical rule; it does not prove that no relevant study exists.'));results.append(box);status.textContent='The engine abstained · '+data.reason;}
  else{
   status.textContent=data.results.length+' leads · '+data.candidate_count+' eligible records · '+data.method+' title similarity';
   data.results.forEach((r,i)=>{const article=element('article',undefined,'paper');const number=element('div',String(i+1).padStart(2,'0'),'number');const content=element('div');const heading=element('h3');const link=element('a',r.title);link.href='https://doi.org/'+encodeURIComponent(r.doi);link.target='_blank';link.rel='noopener noreferrer';heading.append(link);content.append(heading,element('div',r.year+' · '+r.type.replaceAll('-',' ')+' · '+r.doi,'meta'));const terms=element('div',undefined,'terms');terms.setAttribute('aria-label','Matching title terms');r.terms.forEach(t=>terms.append(element('span',t,'term')));content.append(terms);const score=element('div',r.score.toFixed(3),'score');score.append(element('span','similarity / not confidence'));article.append(number,content,score);results.append(article);});
  }
 }catch(error){status.textContent=error.message;results.append(element('p','Check your input and that the local server is running.'));}
 finally{submit.disabled=false;}
}
form.addEventListener('submit',event=>{event.preventDefault();search();});
fetch('/api/catalog').then(r=>{if(!r.ok)throw new Error('Catalog unavailable');return r.json();}).then(data=>{document.querySelector('#catalog-count').textContent=data.count;const examples=document.querySelector('#examples');['graph neural networks','time series forecasting','sourdough starter feeding schedule'].forEach(text=>{const button=element('button',text);button.type='button';button.addEventListener('click',()=>{query.value=text;search();});examples.append(button);});}).catch(()=>{status.textContent='The local catalog is unavailable.';});
