"use strict";
const bookSearch = BOOK_SEARCH_DATA;
const bookRoot = document.body.dataset.root || "";
const searchInput = document.getElementById("book-search");
const searchResults = document.getElementById("search-results");
const chapterNav = document.querySelector("#book-nav nav");
searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLocaleLowerCase();
  searchResults.replaceChildren(); chapterNav.hidden = !!query;
  if (!query) return;
  const matches = bookSearch.filter(item => (item.title + " " + item.text).toLocaleLowerCase().includes(query)).slice(0, 20);
  const message = document.createElement("p");
  message.textContent = matches.length ? "找到以下章节与概念" : "未找到。试试：工具、记忆、恢复、审批。";
  searchResults.append(message);
  matches.forEach(item => {
    const anchor = document.createElement("a");
    anchor.href = bookRoot + item.url; anchor.textContent = item.title;
    searchResults.append(anchor);
  });
});
const menuButton = document.getElementById("menu-toggle");
const shade = document.getElementById("nav-shade");
const bookSide = document.getElementById("book-nav");
const mobileBreakpoint = window.matchMedia("(max-width:820px)");
function closeBookMenu() {
  document.body.classList.remove("menu-open"); shade.hidden = true;
  menuButton.setAttribute("aria-expanded", "false"); document.body.style.overflow = "";
  bookSide.inert = mobileBreakpoint.matches;
}
menuButton.addEventListener("click", () => {
  const opening = !document.body.classList.contains("menu-open");
  closeBookMenu();
  if (opening) {
    bookSide.inert = false;
    document.body.classList.add("menu-open"); shade.hidden = false;
    menuButton.setAttribute("aria-expanded", "true"); document.body.style.overflow = "hidden";
    searchInput.focus();
  }
});
mobileBreakpoint.addEventListener("change", closeBookMenu);
closeBookMenu();
shade.addEventListener("click", closeBookMenu);
bookSide.addEventListener("click", event => {
  if (event.target instanceof Element && event.target.closest("a")) closeBookMenu();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && document.body.classList.contains("menu-open")) {
    closeBookMenu(); menuButton.focus();
  }
});
let readingSize = 17;
try { readingSize = Number(localStorage.getItem("agent-book-font")) || 17; } catch (_) {}
function setReadingSize(value) {
  readingSize = Math.max(15, Math.min(21, value));
  document.documentElement.style.setProperty("--reading-size", readingSize + "px");
  try { localStorage.setItem("agent-book-font", String(readingSize)); } catch (_) {}
}
setReadingSize(readingSize);
document.getElementById("font-down").addEventListener("click", () => setReadingSize(readingSize - 1));
document.getElementById("font-up").addEventListener("click", () => setReadingSize(readingSize + 1));
