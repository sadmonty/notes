from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String, nullable=False)
    tags = db.Column(db.String, nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    selected_tag = request.args.get('tag')
    entries_raw = Entry.query.order_by(Entry.id.desc()).all()
    entries = []
    tags_set = set()

    for entry in entries_raw:
        entry_tags = [t.strip() for t in entry.tags.split(',')] if entry.tags else []

        # Собираем все теги
        tags_set.update(entry_tags)

        # Фильтрация
        if selected_tag == '_none':
            if entry.tags:  # если есть теги — пропустить
                continue
        elif selected_tag and selected_tag not in entry_tags:
            continue

        try:
            parsed = json.loads(entry.content)
        except Exception:
            parsed = {"blocks": [{"type": "paragraph", "data": {"text": "[ошибка чтения]"}}]}
        entries.append({
            "created_at": entry.created_at,
            "blocks": parsed.get("blocks", []),
            "tags": entry.tags
        })

    return render_template(
        'index.html',
        entries=entries,
        all_tags=sorted(tags_set),
        selected_tag=selected_tag
    )

@app.route('/save', methods=['POST'])
def save():
    data = request.get_json()
    content = data.get('content')
    timestamp = data.get('timestamp')
    tags = data.get('tags', '')

    entry = Entry.query.filter_by(created_at=timestamp).first()
    if entry:
        entry.content = content
        entry.tags = tags
    else:
        entry = Entry(content=content, created_at=timestamp, tags=tags)
        db.session.add(entry)

    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': 0, 'message': 'Нет файла'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': 0, 'message': 'Пустое имя файла'}), 400

    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], year, month, day)
    os.makedirs(target_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(target_dir, filename)
    file.save(filepath)

    file_url = f"/{filepath.replace(os.path.sep, '/')}"
    return jsonify({'success': 1, 'file': {'url': file_url}})

@app.route('/tags')
def get_tags():
    entries = Entry.query.all()
    tags_set = set()
    for entry in entries:
        if entry.tags:
            for tag in entry.tags.split(','):
                tags_set.add(tag.strip())
    return jsonify(sorted(tags_set))

if __name__ == '__main__':
    app.run(debug=True, port=7010)
