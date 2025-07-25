// Special effect when changing page
document.addEventListener("DOMContentLoaded", function () {
    const links = document.querySelectorAll("a:not([target='_blank'])");
    
    links.forEach(link => {
        link.addEventListener("click", function (e) {
        // Prevent fade on hash links or JS-only links
        if (
            this.href === window.location.href ||
            this.getAttribute("href").startsWith("#") ||
            this.hasAttribute("data-no-fade")
        ) return;
    
        e.preventDefault();
        document.body.classList.add("fade-out");
    
        setTimeout(() => {
            window.location.href = this.href;
        }, 500); 
        });
    });

    window.addEventListener("load", () => {
        document.body.style.opacity = "1";
      });
});