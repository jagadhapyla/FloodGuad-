// FloodGuard AI - Core Interactive Engine
document.addEventListener("DOMContentLoaded", function () {
    // ==========================================
    // 0. LOCAL FILE PREVIEW HELPER (file:// PROTOCOL)
    // ==========================================
    if (window.location.protocol === "file:") {
        // Show gentle notice banner
        const notice = document.createElement("div");
        notice.style.background = "#eff6ff";
        notice.style.color = "#1e40af";
        notice.style.padding = "12px 20px";
        notice.style.borderBottom = "1px solid #bfdbfe";
        notice.style.textAlign = "center";
        notice.style.fontSize = "13px";
        notice.style.fontWeight = "600";
        notice.innerHTML = '💡 <strong>Template Preview Mode</strong>: You are viewing this HTML file directly via <code>file:///</code>. To submit live reports and use the database, start your server with <code>python app.py</code> and open <a href="http://127.0.0.1:5000" style="color:#0284c7; text-decoration:underline;">http://127.0.0.1:5000</a>.';
        document.body.insertBefore(notice, document.body.firstChild);

        // Hide raw unrendered Jinja tags
        const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        const nodesToClean = [];
        while (walk.nextNode()) {
            if (walk.currentNode.nodeValue.includes("{%") || walk.currentNode.nodeValue.includes("{{")) {
                nodesToClean.push(walk.currentNode);
            }
        }
        nodesToClean.forEach(node => {
            node.nodeValue = node.nodeValue.replace(/\{%[\s\S]*?%\}/g, "").replace(/\{\{[\s\S]*?\}\}/g, "");
        });
    }

    // ==========================================
    // 1. AUTO-DISMISS FLASH ALERTS & CLOSE BUTTONS
    // ==========================================
    document.querySelectorAll(".alert-dismiss").forEach(button => {
        button.addEventListener("click", function () {
            const alertBox = this.closest(".message");
            if (alertBox) {
                alertBox.style.opacity = "0";
                alertBox.style.transform = "translateY(-10px)";
                setTimeout(() => alertBox.remove(), 300);
            }
        });
    });

    // ==========================================
    // 2. CITIZEN COMPLAINT FORM LOGIC
    // ==========================================
    const complaintForm = document.getElementById("complaintForm");
    const locationButton = document.getElementById("locationButton");
    const locationStatus = document.getElementById("locationStatus");
    const coordinatesDisplay = document.getElementById("coordinates");
    const latInput = document.getElementById("latitude");
    const lonInput = document.getElementById("longitude");
    const accInput = document.getElementById("accuracy");
    const photoInput = document.getElementById("photo");
    const photoPreview = document.getElementById("photoPreview");
    const previewContainer = document.getElementById("photoPreviewContainer");
    const removePhotoBtn = document.getElementById("removePhotoBtn");
    const uploadDropzone = document.getElementById("uploadDropzone");
    const submitBtn = document.getElementById("submitBtn");

    if (locationButton && locationStatus) {
        locationButton.addEventListener("click", function () {
            if (!navigator.geolocation) {
                locationStatus.innerHTML = '<span class="status-error">⚠️ Geolocation is not supported by your browser.</span>';
                return;
            }

            locationStatus.innerHTML = '<span class="status-detecting"><span class="spinner-inline"></span> Detecting your live satellite GPS location...</span>';
            locationButton.disabled = true;
            locationButton.classList.add("loading");

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    const accuracy = position.coords.accuracy;

                    latInput.value = latitude;
                    lonInput.value = longitude;
                    accInput.value = accuracy;

                    if (coordinatesDisplay) {
                        coordinatesDisplay.innerHTML = `
                            <div class="coord-tag"><span class="tag-label">Lat:</span> ${latitude.toFixed(6)}°</div>
                            <div class="coord-tag"><span class="tag-label">Lon:</span> ${longitude.toFixed(6)}°</div>
                            <div class="coord-tag"><span class="tag-label">Accuracy:</span> ±${Math.round(accuracy)}m</div>
                        `;
                        coordinatesDisplay.style.display = "flex";
                    }

                    if (accuracy > 100) {
                        locationStatus.innerHTML = `<span class="status-warning">⚠️ GPS accuracy is weak (±${Math.round(accuracy)}m). For highest precision, try outdoors under an open sky.</span>`;
                    } else {
                        locationStatus.innerHTML = `<span class="status-success">✓ Live GPS locked (Accuracy: ±${Math.round(accuracy)}m)</span>`;
                        locationButton.classList.add("btn-success");
                        locationButton.innerHTML = '<span>✓ Location Locked</span>';
                    }

                    locationButton.disabled = false;
                    locationButton.classList.remove("loading");
                },
                function (error) {
                    const errorMessages = {
                        1: "Location permission was denied. Please allow location access in your browser settings.",
                        2: "Position unavailable. Please enable device GPS / location services.",
                        3: "GPS request timed out. Please try clicking again."
                    };

                    locationStatus.innerHTML = `<span class="status-error">⚠️ ${errorMessages[error.code] || "Failed to detect location."}</span>`;
                    locationButton.disabled = false;
                    locationButton.classList.remove("loading");
                },
                {
                    enableHighAccuracy: true,
                    timeout: 25000,
                    maximumAge: 0
                }
            );
        });
    }

    // Photo selection and preview
    if (photoInput) {
        function handleFileSelection(file) {
            if (!file) return;

            const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
            if (!allowedTypes.includes(file.type)) {
                alert("Please select a valid image file (JPEG, PNG, or WEBP).");
                photoInput.value = "";
                if (previewContainer) previewContainer.style.display = "none";
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                alert("The selected photo exceeds the 5 MB limit. Please choose a smaller image.");
                photoInput.value = "";
                if (previewContainer) previewContainer.style.display = "none";
                return;
            }

            const objectUrl = URL.createObjectURL(file);
            if (photoPreview) {
                photoPreview.src = objectUrl;
            }
            if (previewContainer) {
                previewContainer.style.display = "block";
            }
            if (uploadDropzone) {
                uploadDropzone.classList.add("has-file");
            }
        }

        photoInput.addEventListener("change", function () {
            if (photoInput.files && photoInput.files[0]) {
                handleFileSelection(photoInput.files[0]);
            }
        });

        if (removePhotoBtn) {
            removePhotoBtn.addEventListener("click", function () {
                photoInput.value = "";
                if (previewContainer) previewContainer.style.display = "none";
                if (uploadDropzone) uploadDropzone.classList.remove("has-file");
            });
        }

        // Drag and drop support
        if (uploadDropzone) {
            ["dragenter", "dragover"].forEach(eventName => {
                uploadDropzone.addEventListener(eventName, function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadDropzone.classList.add("dragover");
                });
            });

            ["dragleave", "drop"].forEach(eventName => {
                uploadDropzone.addEventListener(eventName, function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadDropzone.classList.remove("dragover");
                });
            });

            uploadDropzone.addEventListener("drop", function (e) {
                const dt = e.dataTransfer;
                if (dt && dt.files && dt.files.length) {
                    photoInput.files = dt.files;
                    handleFileSelection(dt.files[0]);
                }
            });
        }
    }

    // Citizen Form submission validation
    if (complaintForm) {
        complaintForm.addEventListener("submit", function (event) {
            const lat = latInput ? latInput.value.trim() : "";
            const lon = lonInput ? lonInput.value.trim() : "";
            const acc = accInput ? parseFloat(accInput.value) : 0;

            if (!lat || !lon) {
                event.preventDefault();
                alert("Please click 'Detect Live GPS Location' before submitting. Emergency teams need exact coordinates.");
                if (locationButton) locationButton.focus();
                return;
            }

            if (acc > 100) {
                event.preventDefault();
                alert("Your GPS accuracy is beyond 100m. Please try outdoors for an accurate satellite signal.");
                return;
            }

            if (!photoInput || !photoInput.files || !photoInput.files.length) {
                event.preventDefault();
                alert("Please capture or upload a photo of the flooded area.");
                if (photoInput) photoInput.focus();
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-inline"></span> Submitting Incident Report...';
            }
        });
    }

    // ==========================================
    // 3. AGENT DASHBOARD SEARCH & FILTERING
    // ==========================================
    const searchInput = document.getElementById("dashboardSearch");
    const filterTabs = document.querySelectorAll(".filter-tab");
    const problemCards = document.querySelectorAll(".problem-card");

    let currentFilter = "all";
    let currentSearchTerm = "";

    function filterProblems() {
        let visibleCount = 0;

        problemCards.forEach(card => {
            const cardStatus = (card.getAttribute("data-status") || "").toLowerCase();
            const cardText = card.innerText.toLowerCase();

            const matchesStatus = (currentFilter === "all") || (cardStatus === currentFilter);
            const matchesSearch = !currentSearchTerm || cardText.includes(currentSearchTerm);

            if (matchesStatus && matchesSearch) {
                card.style.display = "block";
                visibleCount++;
            } else {
                card.style.display = "none";
            }
        });

        const noResultsMessage = document.getElementById("noResultsMessage");
        if (noResultsMessage) {
            noResultsMessage.style.display = visibleCount === 0 ? "block" : "none";
        }
    }

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            currentSearchTerm = this.value.trim().toLowerCase();
            filterProblems();
        });
    }

    if (filterTabs.length > 0) {
        filterTabs.forEach(tab => {
            tab.addEventListener("click", function () {
                filterTabs.forEach(t => t.classList.remove("active"));
                this.classList.add("active");
                currentFilter = this.getAttribute("data-filter").toLowerCase();
                filterProblems();
            });
        });
    }

    // ==========================================
    // 4. PHOTO LIGHTBOX / MODAL
    // ==========================================
    const modal = document.getElementById("photoModal");
    const modalImg = document.getElementById("modalImage");
    const modalCaption = document.getElementById("modalCaption");
    const modalClose = document.getElementById("modalClose");

    if (modal && modalImg) {
        document.querySelectorAll(".expandable-photo").forEach(img => {
            img.addEventListener("click", function () {
                modal.style.display = "flex";
                modalImg.src = this.getAttribute("data-full") || this.src;
                if (modalCaption) {
                    modalCaption.textContent = this.getAttribute("data-caption") || "Incident Location Photo";
                }
            });
        });

        if (modalClose) {
            modalClose.addEventListener("click", function () {
                modal.style.display = "none";
            });
        }

        modal.addEventListener("click", function (e) {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        });
    }
});
