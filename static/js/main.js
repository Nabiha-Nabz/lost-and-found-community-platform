document.querySelector('.nav-toggle')?.addEventListener('click', event => {
  const links = document.querySelector('#nav-links');
  const open = links.classList.toggle('open');
  event.currentTarget.setAttribute('aria-expanded', String(open));
});
document.querySelectorAll('.alert button').forEach(button => button.addEventListener('click', () => button.parentElement.remove()));
document.querySelectorAll('[data-confirm]').forEach(form => form.addEventListener('submit', event => {
  if (!window.confirm(form.dataset.confirm)) event.preventDefault();
}));
document.querySelectorAll('button[data-confirm]').forEach(button => button.addEventListener('click', event => {
  if (!window.confirm(button.dataset.confirm)) event.preventDefault();
}));
const photos = document.querySelector('#photos');
photos?.addEventListener('change', () => {
  const preview = document.querySelector('#image-preview'); preview.innerHTML = '';
  [...photos.files].forEach(file => { const img=document.createElement('img'); img.src=URL.createObjectURL(file); img.alt=`Preview of ${file.name}`; preview.appendChild(img); });
});
