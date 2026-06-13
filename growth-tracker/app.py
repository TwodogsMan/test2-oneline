"""
成长记录网站 — Flask 后端
个人成长轨迹记录，支持照片和文档上传
"""
import os
import json
import sqlite3
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory
)
from werkzeug.utils import secure_filename

# ── App 配置 ────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'growth-tracker-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
PHOTO_DIR = os.path.join(UPLOAD_DIR, 'photos')
DOC_DIR = os.path.join(UPLOAD_DIR, 'documents')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'growth.db')

# 确保目录存在
for d in [PHOTO_DIR, DOC_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

# 允许的文件类型
ALLOWED_PHOTOS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_DOCS = {'pdf', 'doc', 'docx', 'txt', 'md'}

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 总上传限制


# ── 数据库 ──────────────────────────────────────────────
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            photos      TEXT    DEFAULT '[]',
            documents   TEXT    DEFAULT '[]',
            created_at  TEXT    NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# ── 辅助函数 ────────────────────────────────────────────
def allowed_file(filename, allowed_set):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_set


def save_files(files, target_dir, allowed_set):
    """保存上传文件，返回文件名列表"""
    saved = []
    for f in files:
        if f and f.filename and allowed_file(f.filename, allowed_set):
            filename = secure_filename(f.filename)
            # 加时间戳防重名
            name, ext = os.path.splitext(filename)
            unique_name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            f.save(os.path.join(target_dir, unique_name))
            saved.append(unique_name)
    return saved


def delete_files(filenames, target_dir):
    """删除指定文件"""
    if not filenames:
        return
    for fname in filenames:
        filepath = os.path.join(target_dir, fname)
        if os.path.isfile(filepath):
            os.remove(filepath)


# ── 路由 ────────────────────────────────────────────────
@app.route('/')
def index():
    """首页 — 时间线展示"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    offset = (page - 1) * per_page

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    records = conn.execute(
        "SELECT * FROM records ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    conn.close()

    # 解析 JSON 字段
    records_list = []
    for r in records:
        rec = dict(r)
        rec['photos'] = json.loads(rec['photos'])
        rec['documents'] = json.loads(rec['documents'])
        records_list.append(rec)

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template('index.html',
                           records=records_list,
                           page=page,
                           total_pages=total_pages)


@app.route('/add', methods=['GET', 'POST'])
def add():
    """添加新记录"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not date:
            flash('标题和日期为必填项', 'error')
            return render_template('add.html')

        # 保存照片
        photo_files = request.files.getlist('photos')
        photos = save_files(photo_files, PHOTO_DIR, ALLOWED_PHOTOS)

        # 保存文档
        doc_files = request.files.getlist('documents')
        documents = save_files(doc_files, DOC_DIR, ALLOWED_DOCS)

        conn = get_db()
        conn.execute(
            "INSERT INTO records (title, date, description, photos, documents, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, date, description, json.dumps(photos),
             json.dumps(documents), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        flash('🎉 成长记录添加成功！', 'success')
        return redirect(url_for('index'))

    return render_template('add.html')


@app.route('/record/<int:record_id>')
def view(record_id):
    """查看记录详情"""
    conn = get_db()
    record = conn.execute(
        "SELECT * FROM records WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()

    if not record:
        flash('记录不存在', 'error')
        return redirect(url_for('index'))

    rec = dict(record)
    rec['photos'] = json.loads(rec['photos'])
    rec['documents'] = json.loads(rec['documents'])

    return render_template('view.html', record=rec)


@app.route('/record/<int:record_id>/edit', methods=['GET', 'POST'])
def edit(record_id):
    """编辑记录"""
    conn = get_db()
    record = conn.execute(
        "SELECT * FROM records WHERE id = ?", (record_id,)
    ).fetchone()

    if not record:
        conn.close()
        flash('记录不存在', 'error')
        return redirect(url_for('index'))

    rec = dict(record)
    rec['photos'] = json.loads(rec['photos'])
    rec['documents'] = json.loads(rec['documents'])

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not date:
            flash('标题和日期为必填项', 'error')
            return render_template('edit.html', record=rec)

        # ── 处理照片 ──
        photos = rec['photos']

        # 删除被选中的旧照片
        delete_photos = request.form.getlist('delete_photos')
        if delete_photos:
            delete_files(delete_photos, PHOTO_DIR)
            photos = [p for p in photos if p not in delete_photos]

        # 添加新照片
        new_photos = save_files(
            request.files.getlist('photos'), PHOTO_DIR, ALLOWED_PHOTOS
        )
        photos.extend(new_photos)

        # ── 处理文档 ──
        documents = rec['documents']

        # 删除被选中的旧文档
        delete_docs = request.form.getlist('delete_documents')
        if delete_docs:
            delete_files(delete_docs, DOC_DIR)
            documents = [d for d in documents if d not in delete_docs]

        # 添加新文档
        new_docs = save_files(
            request.files.getlist('documents'), DOC_DIR, ALLOWED_DOCS
        )
        documents.extend(new_docs)

        conn.execute(
            "UPDATE records SET title=?, date=?, description=?, photos=?, documents=? "
            "WHERE id=?",
            (title, date, description, json.dumps(photos),
             json.dumps(documents), record_id)
        )
        conn.commit()
        conn.close()

        flash('✅ 记录更新成功！', 'success')
        return redirect(url_for('view', record_id=record_id))

    conn.close()
    return render_template('edit.html', record=rec)


@app.route('/record/<int:record_id>/delete', methods=['POST'])
def delete(record_id):
    """删除记录"""
    conn = get_db()
    record = conn.execute(
        "SELECT * FROM records WHERE id = ?", (record_id,)
    ).fetchone()

    if not record:
        conn.close()
        flash('记录不存在', 'error')
        return redirect(url_for('index'))

    rec = dict(record)
    # 清理关联文件
    delete_files(json.loads(rec['photos']), PHOTO_DIR)
    delete_files(json.loads(rec['documents']), DOC_DIR)

    conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    flash('🗑️ 记录已删除', 'success')
    return redirect(url_for('index'))


@app.route('/uploads/photos/<path:filename>')
def serve_photo(filename):
    """提供照片文件访问"""
    return send_from_directory(PHOTO_DIR, filename)


@app.route('/uploads/documents/<path:filename>')
def serve_document(filename):
    """提供文档文件下载"""
    return send_from_directory(DOC_DIR, filename, as_attachment=True)


# ── 启动 ────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("成长记录网站已启动: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
