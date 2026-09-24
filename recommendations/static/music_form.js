const MAX_SEED_SONGS = 2;
const MAX_GENRES = 10;
const ALL_GENRES = [
  "acoustic", "afrobeat", "alt-rock", "ambient", "black-metal", "blues",
  "breakbeat", "cantopop", "chicago-house", "chill", "classical", "club",
  "comedy", "country", "dance", "dancehall", "death-metal", "deep-house",
  "detroit-techno", "disco", "drum-and-bass", "dub", "dubstep", "edm",
  "electro", "electronic", "emo", "folk", "forro", "french", "funk",
  "garage", "german", "gospel", "goth", "grindcore", "groove", "guitar",
  "hard-rock", "hardcore", "hardstyle", "heavy-metal", "hip-hop", "house",
  "indian", "indie-pop", "industrial", "jazz", "k-pop", "metal",
  "metalcore", "minimal-techno", "new-age", "opera", "party", "piano",
  "pop", "pop-film", "power-pop", "progressive-house", "psych-rock",
  "punk", "punk-rock", "rock", "rock-n-roll", "romance", "sad", "salsa",
  "samba", "sertanejo", "show-tunes", "singer-songwriter", "ska", "sleep",
  "songwriter", "soul", "spanish", "swedish", "tango", "techno", "trance",
  "trip-hop"
];

const state = {
  selectedSongs: new Map(),
  selectedGenres: new Set(),
  lastResults: [],
};

const el = {
  form: document.getElementById("playlistForm"),
  searchInput: document.getElementById("songName"),
  searchButton: document.getElementById("searchButton"),
  searchWrap: document.querySelector(".search-wrap"),
  searchResults: document.getElementById("searchResults"),
  selectedSongs: document.getElementById("selectedSongs"),
  message: document.getElementById("message"),
  genrePicker: document.getElementById("genrePicker"),
  genreTrigger: document.getElementById("genreTrigger"),
  genreMenu: document.getElementById("genreMenu"),
  genreInput: document.getElementById("genreInput"),
  genreOptions: document.getElementById("genreOptions"),
  genreChips: document.getElementById("genreChips"),
  genrePlaceholder: document.getElementById("genrePlaceholder"),
  clearGenres: document.getElementById("clearGenres"),
  eraStart: document.getElementById("eraStart"),
  eraEnd: document.getElementById("eraEnd"),
  eraLabel: document.getElementById("eraLabel"),
  playlistSection: document.getElementById("playlistSection"),
  playlistList: document.getElementById("playlistList"),
  playlistSummary: document.getElementById("playlistSummary"),
  spotifyPlayer: document.getElementById("spotifyPlayer"),
  spotifyPlayerLabel: document.getElementById("spotifyPlayerLabel"),
  spotifyEmbed: document.getElementById("spotifyEmbed"),
};

el.searchButton.addEventListener("click", searchSpotify);
el.searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    searchSpotify();
  }
  if (event.key === "Escape") {
    closeSearchResults();
  }
});
el.form.addEventListener("submit", submitPlaylistRequest);
document.querySelectorAll("[data-focus-search]").forEach((button) => {
  button.addEventListener("click", () => el.searchInput.focus());
});
el.genreTrigger.addEventListener("click", toggleGenreMenu);
el.genreInput.addEventListener("input", renderGenreOptions);
el.clearGenres.addEventListener("click", () => {
  state.selectedGenres.clear();
  renderGenrePicker();
});
document.addEventListener("click", (event) => {
  if (!el.genrePicker.contains(event.target)) {
    closeGenreMenu();
  }
  if (!el.searchWrap.contains(event.target)) {
    closeSearchResults();
  }
});
[el.eraStart, el.eraEnd].forEach((range) => range.addEventListener("input", syncEraRange));

renderGenrePicker();
syncEraRange();

async function searchSpotify() {
  const query = el.searchInput.value.trim();
  if (!query) {
    setMessage("Enter a song or artist to search.", "warning");
    return;
  }

  setMessage("");
  setSearchLoading(true);
  showResultsPanel("Searching Spotify...");

  try {
    const response = await fetch(`/search/?query=${encodeURIComponent(query)}`);
    if (!response.ok) {
      throw new Error(`Search failed with ${response.status}`);
    }

    const results = await response.json();
    state.lastResults = Array.isArray(results) ? results : [];
    renderSearchResults();
  } catch (error) {
    console.error(error);
    showResultsPanel("Search is temporarily unavailable. Please try again.");
    setMessage("Could not reach the search API.", "error");
  } finally {
    setSearchLoading(false);
  }
}

function renderSearchResults() {
  el.searchResults.hidden = false;
  el.searchResults.innerHTML = "";

  if (state.lastResults.length === 0) {
    el.searchResults.textContent = "No songs found. Try a different search.";
    return;
  }
        
  state.lastResults.slice(0, 8).forEach((track) => {

    const isSelected = state.selectedSongs.has(track.track_id);
    const item = document.createElement("button");
    item.className = "result-item";
    item.type = "button";
    item.disabled = isSelected || state.selectedSongs.size >= MAX_SEED_SONGS;
    item.addEventListener("click", () => addSong(track));
    item.innerHTML = `
      <span class="song-copy">
        <strong>${escapeHtml(track.track_name || "Unknown track")}</strong>
        <span>${escapeHtml(track.artist_name || "Unknown artist")}${track.genre ? ` - ${escapeHtml(formatGenreLabel(track.genre))}` : ""}</span>
      </span>
      <span class="add-icon">${isSelected ? "Added" : "Add"}</span>
    `;
    el.searchResults.appendChild(item);
  });

}

function addSong(track) {
  if (state.selectedSongs.size >= MAX_SEED_SONGS || state.selectedSongs.has(track.track_id)) {
    return;
  }

  state.selectedSongs.set(track.track_id, track);
  if (track.genre && ALL_GENRES.includes(track.genre)) {
    state.selectedGenres.add(track.genre);
  }
  el.searchResults.hidden = true;
  el.searchInput.value = "";
  setMessage("");
  renderSelectedSongs();
  renderGenrePicker();
}

function removeSong(trackId) {
  const removedTrack = state.selectedSongs.get(trackId);
  state.selectedSongs.delete(trackId);
  if (removedTrack?.genre) {
    const stillUsed = Array.from(state.selectedSongs.values()).some((track) => track.genre === removedTrack.genre);
    if (!stillUsed) {
      state.selectedGenres.delete(removedTrack.genre);  
      renderGenrePicker();
    }
  }
  renderSelectedSongs();
  if (state.lastResults.length > 0) {
    renderSearchResults();
  }
}

function renderSelectedSongs() {
  el.selectedSongs.innerHTML = "";
  const songs = Array.from(state.selectedSongs.values());

  songs.forEach((track) => {
    const card = document.createElement("article");
    card.className = "selected-song";
    card.innerHTML = `
      <span class="song-copy">
        <strong>${escapeHtml(track.track_name || "Unknown track")}</strong>
        <span>${escapeHtml(track.artist_name || "Unknown artist")}${track.genre ? ` - ${escapeHtml(formatGenreLabel(track.genre))}` : ""}</span>
      </span>
      <button type="button" aria-label="Remove ${escapeHtml(track.track_name || "song")}">Remove</button>
    `;
    card.querySelector("button").addEventListener("click", () => removeSong(track.track_id));
    el.selectedSongs.appendChild(card);
  });

  for (let i = songs.length; i < MAX_SEED_SONGS; i += 1) {
    const empty = document.createElement("button");
    empty.className = "empty-slot";
    empty.type = "button";
    empty.textContent = i === 0 ? "Add your first song" : "Add a second song";
    empty.addEventListener("click", () => el.searchInput.focus());
    el.selectedSongs.appendChild(empty);
  }

  renderHiddenInputs();
}

function renderHiddenInputs() {
  document.querySelectorAll("[data-dynamic-input]").forEach((input) => input.remove());
  Array.from(state.selectedSongs.keys()).forEach((trackId) => addHiddenInput("track_ids", trackId));
  Array.from(state.selectedGenres).forEach((genre) => addHiddenInput("genres", genre));
}

function addHiddenInput(name, value) {
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = name;
  input.value = value;
  input.dataset.dynamicInput = "true";
  el.form.appendChild(input);
}

async function submitPlaylistRequest(event) {
  event.preventDefault();
  renderHiddenInputs();

  try {

    buttonElement = document.getElementById("generate-button");
    buttonElement.disabled = true;
    buttonElement.textContent = "Generating...";
    buttonElement.ariaLabel = "Generating...";
    const formData = new FormData(el.form);

    const response = await fetch('/', {
      method: "POST",
      headers: { Accept: "application/json" },
      body: formData,
    });

    if (!response.ok) {
      buttonElement.textContent = "Make Playlist";
      buttonElement.ariaLabel = "Make Playlist";
      buttonElement.disabled = false;
      throw new Error(`Recommendation failed with ${response.status}`);
     
    }

    const data = await response.json();

    renderPlaylist(normalizeRecommendations(data));

    buttonElement.textContent = "Make Playlist";
    buttonElement.ariaLabel = "Make Playlist";
    buttonElement.disabled = false;
  } catch (error) {
    console.error(error);
    setMessage("Could not make a playlist right now. Please try again.", "error");

    buttonElement.textContent = "Make Playlist";
    buttonElement.ariaLabel = "Make Playlist";
    buttonElement.disabled = false;
  }
}

function renderPlaylist(tracks) {
  el.playlistList.innerHTML = "";
  el.playlistSummary.textContent = `${tracks.length} songs based on your taste`;

  tracks.forEach((track, index) => {
    const item = document.createElement("li");
    item.className = "playlist-item";
    item.innerHTML = `
      <span class="track-number">${index + 1}</span>
      <span class="song-copy">
        <strong>${escapeHtml(track.title)}</strong>
        <span>${escapeHtml(track.artist)}</span>
      </span>
      <span class="duration">${track.duration || "--:--"}</span>
      <button class="track-play" type="button" ${track.trackId ? "" : "disabled"}>Play</button>
    `;
    item.querySelector(".track-play").addEventListener("click", () => playSpotifyTrack(track));
    el.playlistList.appendChild(item);
  });

  el.playlistSection.hidden = false;
  el.playlistSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function normalizeRecommendations(result) {

  const tracks = Array.isArray(result) ? result : [];
  if (tracks.length === 0) {
    return [];
  }

  return tracks.map((track, index) => ({
    title: track.track_name || track.title || `Recommendation ${index + 1}`,
    artist: track.artist_names || track.artist || track.track_id || "Unknown artist",
    duration: track.duration || "--:--",
    trackId: track.track_id || track.id || "",
  }));
}

function playSpotifyTrack(track) {
  if (!track.trackId) {
    return;
  }

  el.spotifyEmbed.src = `https://open.spotify.com/embed/track/${encodeURIComponent(track.trackId)}?utm_source=generator`;
  el.spotifyPlayerLabel.textContent = `${track.title} - ${track.artist}`;
  el.spotifyPlayer.hidden = false;
  el.spotifyPlayer.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function toggleGenreMenu() {
  const isOpen = !el.genreMenu.hidden;
  el.genreMenu.hidden = isOpen;
  el.genreTrigger.setAttribute("aria-expanded", String(!isOpen));
  if (!isOpen) {
    el.genreInput.focus();
  }
}

function closeGenreMenu() {
  el.genreMenu.hidden = true;
  el.genreTrigger.setAttribute("aria-expanded", "false");
}

function renderGenrePicker() {
  el.genreChips.innerHTML = "";
  el.genrePlaceholder.hidden = state.selectedGenres.size > 0;

  state.selectedGenres.forEach((genre) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    const genreLabel = formatGenreLabel(genre);
    chip.innerHTML = `${escapeHtml(genreLabel)} <button type="button" aria-label="Remove ${escapeHtml(genreLabel)}">x</button>`;
    chip.querySelector("button").addEventListener("click", (event) => {
      event.stopPropagation();
      state.selectedGenres.delete(genre);
      renderGenrePicker();
    });
    el.genreChips.appendChild(chip);
  });

  renderGenreOptions();
  renderHiddenInputs();
}

function renderGenreOptions() {
  const filter = el.genreInput.value.trim().toLowerCase();
  el.genreOptions.innerHTML = "";

  ALL_GENRES
    .filter((genre) => genre.toLowerCase().includes(filter))
    .forEach((genre) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "genre-option";
      option.dataset.selected = String(state.selectedGenres.has(genre));
      option.textContent = formatGenreLabel(genre);
      option.addEventListener("click", () => {
        if (state.selectedGenres.has(genre)) {
          state.selectedGenres.delete(genre);
        } else {
          if (state.selectedGenres.size >= MAX_GENRES) {
            setMessage(`Choose up to ${MAX_GENRES} genres.`, "warning");
            return;
          }
          state.selectedGenres.add(genre);
        }
        renderGenrePicker();
      });
      el.genreOptions.appendChild(option);
    });
}



function syncEraRange() {
  let start = Number(el.eraStart.value);
  let end = Number(el.eraEnd.value);

  if (start > end) {
    if (document.activeElement === el.eraStart) {
      end = start;
      el.eraEnd.value = String(end);
    } else {
      start = end;
      el.eraStart.value = String(start);
    }
  }

  const min = Number(el.eraStart.min);
  const max = Number(el.eraStart.max);
  const startPercent = ((start - min) / (max - min)) * 100;
  const endPercent = ((end - min) / (max - min)) * 100;
  const range = el.eraStart.closest(".dual-range");

  range.style.setProperty("--range-start", `${startPercent}%`);
  range.style.setProperty("--range-end", `${endPercent}%`);
  el.eraLabel.textContent = `${start} - ${end}`;
}

function formatGenreLabel(genre) {
  return genre
    .split("-")
    .map((word) => word.toUpperCase() === "K" ? "K" : word.charAt(0).toUpperCase() + word.slice(1))
    .join("-");
}

function showResultsPanel(text) {
  el.searchResults.hidden = false;
  el.searchResults.textContent = text;
}

function closeSearchResults() {
  el.searchResults.hidden = true;
}

function setSearchLoading(isLoading) {
  el.searchButton.disabled = isLoading;
  el.searchButton.textContent = isLoading ? "Searching" : "Search";
}

function setMessage(text, tone = "") {
  el.message.textContent = text;
  el.message.dataset.tone = tone;
}

function getInitial(value = "") {
  return escapeHtml(value.trim().charAt(0).toUpperCase() || "R");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
