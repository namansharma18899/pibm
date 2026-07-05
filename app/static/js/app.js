document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".star-rating").forEach(function (container) {
    var input = container.querySelector('input[type="hidden"]');
    var stars = Array.from(container.querySelectorAll(".star"));
    var resetBtn = container.querySelector(".star-reset");

    function render(value) {
      stars.forEach(function (star) {
        var v = parseInt(star.dataset.value);
        if (v <= value) {
          star.textContent = "★";
          star.classList.add("active");
        } else {
          star.textContent = "☆";
          star.classList.remove("active");
        }
      });
    }

    stars.forEach(function (star) {
      star.addEventListener("click", function () {
        var val = parseInt(this.dataset.value);
        input.value = val;
        render(val);
      });

      star.addEventListener("mouseenter", function () {
        render(parseInt(this.dataset.value));
      });
    });

    container.addEventListener("mouseleave", function () {
      render(parseInt(input.value) || 0);
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        input.value = 0;
        render(0);
      });
    }

    render(parseInt(input.value) || 0);
  });

  document.querySelectorAll(".category-reset").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var field = this.dataset.field;
      var container = document.querySelector('[data-category="' + field + '"]');
      if (!container) return;
      container.querySelectorAll('input[type="radio"]').forEach(function (radio) {
        radio.checked = false;
      });
    });
  });
});
