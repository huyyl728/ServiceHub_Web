/* Optional Google Analytics 4 integration.
   1) Set MEASUREMENT_ID to your own G-XXXXXXXXXX ID.
   2) The script loads only after the visitor opts in using localStorage key "servicehub_analytics_consent" = "yes".
   3) Do not enable before publishing an appropriate privacy notice/consent flow.
*/
(() => {
  const MEASUREMENT_ID = ''; // Configure your own GA4 Measurement ID before deployment.
  if (!MEASUREMENT_ID || localStorage.getItem('servicehub_analytics_consent') !== 'yes') return;
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(MEASUREMENT_ID)}`;
  document.head.appendChild(script);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function(){ window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', MEASUREMENT_ID, { anonymize_ip: true });
})();
