document.addEventListener('DOMContentLoaded', () => {
  const select = document.querySelector('select#id_email_template');
  if (select) {
    select.addEventListener('change', (e) => {
      document.querySelectorAll('a[href*="preview_prize"]').forEach(a => {
        const newTemplate = e.target.value;
        a.href = a.href.replace(/\d+$/, newTemplate);
      });
    });
  }
});
