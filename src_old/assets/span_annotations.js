(function () {
  function clampPopover(pop, anchor) {
    if (!pop || !anchor) {
      return;
    }

    var margin = 8;
    var anchorRect = anchor.getBoundingClientRect();

    // Measure after display
    var popRect = pop.getBoundingClientRect();

    var desiredLeft = anchorRect.left + anchorRect.width / 2 - popRect.width / 2;
    var minLeft = margin;
    var maxLeft = window.innerWidth - popRect.width - margin;
    if (desiredLeft < minLeft) {
      desiredLeft = minLeft;
    }
    if (desiredLeft > maxLeft) {
      desiredLeft = maxLeft;
    }

    var desiredTop = anchorRect.top - popRect.height - 8;
    if (desiredTop < margin) {
      desiredTop = anchorRect.bottom + 8;
    }

    pop.style.left = desiredLeft + "px";
    pop.style.top = desiredTop + "px";
    pop.style.transform = "none";
  }

  function handleFocusIn(e) {
    var anchor = e.target.closest(".span-annotation");
    if (!anchor) {
      return;
    }
    var pop = anchor.querySelector(".span-annotation-pop");
    if (!pop) {
      return;
    }

    // Wait for CSS to display popover
    requestAnimationFrame(function () {
      clampPopover(pop, anchor);
    });
  }

  function handleFocusOut(e) {
    var anchor = e.target.closest(".span-annotation");
    if (!anchor) {
      return;
    }
    var pop = anchor.querySelector(".span-annotation-pop");
    if (!pop) {
      return;
    }

    // Reset to defaults
    pop.style.left = "0";
    pop.style.top = "0";
    pop.style.transform = "none";
  }

  document.addEventListener("focusin", handleFocusIn, true);
  document.addEventListener("focusout", handleFocusOut, true);
})();
