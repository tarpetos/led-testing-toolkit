function openModal(src) {
    const modal = document.getElementById("plot-modal");
    const modalImg = document.getElementById("modal-plot-img");
    modal.style.display = "flex";
    modalImg.src = src;
}

function showProcessingAnimation(outputDiv, form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
    }
    outputDiv.innerHTML = `
        <div class="processing-animation">
            <div class="spinner"></div>
            <p>Processing request...</p>
        </div>`;
}

function hideProcessingAnimation(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = false;
    }
}

function updateFileList(fileList, files) {
    fileList.innerHTML = "";
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileItem = document.createElement("div");
        fileItem.className = "file-item";
        fileItem.textContent = file.name;
        fileList.appendChild(fileItem);
    }
}

function setupDropZone(dropZoneId, inputId, fileListId, multiple, callback) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(inputId);
    const fileList = fileListId ? document.getElementById(fileListId) : null;

    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            if (fileList) {
                if (multiple) {
                    updateFileList(fileList, e.target.files);
                } else {
                    updateFileList(fileList, [e.target.files[0]]);
                }
            }
            if (callback) {
                callback(e.target.files);
            }
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drop-zone--over");
    });

    ["dragleave", "dragend"].forEach((type) => {
        dropZone.addEventListener(type, (e) => {
            dropZone.classList.remove("drop-zone--over");
        });
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            if (fileList) {
                if (multiple) {
                    updateFileList(fileList, e.dataTransfer.files);
                } else {
                    updateFileList(fileList, [e.dataTransfer.files[0]]);
                }
            }
            if (callback) {
                callback(e.dataTransfer.files);
            }
        }
        dropZone.classList.remove("drop-zone--over");
    });
}

function setupOutputTypeSwitcher(selectId, inputId) {
    const typeSelector = document.getElementById(selectId);
    const targetInput = document.getElementById(inputId);

    if (!typeSelector || !targetInput) return;

    typeSelector.addEventListener('change', (e) => {
        if (e.target.value === 'db' && targetInput.value.endsWith('.log')) {
            targetInput.value = '';
        }
    });
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
}
