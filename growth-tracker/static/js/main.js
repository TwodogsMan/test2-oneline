/* ============================================================
   成长记录网站 — 前端交互逻辑
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    // ── 文件上传区域：拖拽 & 点击 ──────────────────────
    setupFileUpload('photoUploadArea', 'photos', 'photoPreview', 'image');
    setupFileUpload('docUploadArea', 'documents', 'docPreview', 'document');

    // ── 字符计数 ───────────────────────────────────────
    const descField = document.getElementById('description');
    const charCount = document.getElementById('charCount');
    if (descField && charCount) {
        charCount.textContent = descField.value.length;
        descField.addEventListener('input', function () {
            charCount.textContent = this.value.length;
        });
    }

    // ── 灯箱 ───────────────────────────────────────────
    window.openLightbox = function (src) {
        const lb = document.getElementById('lightbox');
        const img = document.getElementById('lightboxImg');
        if (lb && img) {
            img.src = src;
            lb.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    };

    window.closeLightbox = function () {
        const lb = document.getElementById('lightbox');
        if (lb) {
            lb.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // ESC 关闭灯箱
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeLightbox();
        }
    });

    // ── 删除确认 ───────────────────────────────────────
    window.confirmDelete = function (recordId) {
        if (confirm('确定要删除这条记录吗？此操作不可撤销。')) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/record/' + recordId + '/delete';
            document.body.appendChild(form);
            form.submit();
        }
    };
});


// ── 文件上传设置函数 ──────────────────────────────────
function setupFileUpload(areaId, inputId, previewId, type) {
    const area = document.getElementById(areaId);
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (!area || !input || !preview) return;

    // 点击区域触发文件选择
    area.addEventListener('click', function (e) {
        if (e.target !== input) {
            input.click();
        }
    });

    // 文件选择后预览
    input.addEventListener('change', function () {
        addFilePreviews(this.files, preview, type, input);
    });

    // 拖拽支持
    area.addEventListener('dragover', function (e) {
        e.preventDefault();
        area.classList.add('drag-over');
    });

    area.addEventListener('dragleave', function () {
        area.classList.remove('drag-over');
    });

    area.addEventListener('drop', function (e) {
        e.preventDefault();
        area.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            // 注意：拖拽的文件无法直接赋值给 input.files
            // 需要构造 DataTransfer
            const dt = new DataTransfer();
            for (const file of e.dataTransfer.files) {
                dt.items.add(file);
            }
            input.files = dt.files;
            addFilePreviews(e.dataTransfer.files, preview, type, input);
        }
    });
}


// ── 文件预览 ──────────────────────────────────────────
function addFilePreviews(files, container, type, input) {
    // 照片预览
    if (type === 'image') {
        for (const file of files) {
            if (!file.type.startsWith('image/')) continue;

            const reader = new FileReader();
            reader.onload = function (e) {
                const item = document.createElement('div');
                item.className = 'preview-item';
                item.innerHTML = `
                    <img src="${e.target.result}" alt="${file.name}">
                    <button class="remove-btn" title="移除">✕</button>
                `;
                item.querySelector('.remove-btn').addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    item.remove();
                    removeFileFromInput(input, file.name);
                });
                container.appendChild(item);
            };
            reader.readAsDataURL(file);
        }
    }

    // 文档预览（只显示文件名）
    if (type === 'document') {
        for (const file of files) {
            const item = document.createElement('div');
            item.className = 'doc-preview-item';
            item.innerHTML = `
                <span>📄</span>
                <span>${file.name}</span>
                <span style="color:var(--text-light);font-size:0.8rem">(${formatFileSize(file.size)})</span>
                <button class="remove-btn" title="移除">✕</button>
            `;
            item.querySelector('.remove-btn').addEventListener('click', function (ev) {
                ev.stopPropagation();
                item.remove();
                removeFileFromInput(input, file.name);
            });
            container.appendChild(item);
        }
    }
}


// ── 从 FileList 中移除指定文件 ────────────────────────
function removeFileFromInput(input, filename) {
    // 构造新的 FileList（仅保留不需要删除的文件）
    if (input.files.length === 0) return;

    const dt = new DataTransfer();
    for (const file of input.files) {
        if (file.name !== filename) {
            dt.items.add(file);
        }
    }
    input.files = dt.files;

    // 如果全部移除了，清空 input 以便重新选择相同文件
    if (input.files.length === 0) {
        input.value = '';
    }
}


// ── 文件大小格式化 ────────────────────────────────────
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
