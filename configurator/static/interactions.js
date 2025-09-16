// static/interactions.js
document.addEventListener('DOMContentLoaded', () => {
  const bar = document.querySelector('.progress__bar');
  if(!bar) return;

  const groups = Array.from(document.querySelectorAll('fieldset[data-question-id]'));
  const total = groups.length;

  const isAnswered = (fs) => !!fs.querySelector('input:checked');

  const update = () => {
    const answered = groups.filter(isAnswered).length;
    const pct = total ? Math.round((answered/total)*100) : 0;
    bar.style.width = pct + '%';
  };

  document.addEventListener('change', e => {
    if(e.target.matches('input[type="radio"], input[type="checkbox"]')) update();
  });

  update();
});
