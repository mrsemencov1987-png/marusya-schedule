# -*- coding: utf-8 -*-
"""
Навык "Школьное расписание" для Маруси
"""

from flask import Flask, request, jsonify
import datetime
import json
from data import schedule

app = Flask(__name__)

# Словарь для хранения изменений (в памяти)
# При перезапуске сбрасывается
changes = {}

# Дни недели по-русски
weekdays = [
    "понедельник",
    "вторник", 
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье"
]

def get_current_day():
    """Возвращает текущий день недели по-русски"""
    today = datetime.datetime.today().weekday()
    return weekdays[today]

def get_tomorrow():
    """Возвращает завтрашний день недели по-русски"""
    tomorrow = (datetime.datetime.today().weekday() + 1) % 7
    return weekdays[tomorrow]

def get_day_after_tomorrow():
    """Возвращает послезавтрашний день недели по-русски"""
    day_after = (datetime.datetime.today().weekday() + 2) % 7
    return weekdays[day_after]

def get_next_monday():
    """Возвращает дату следующего понедельника"""
    today = datetime.date.today()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + datetime.timedelta(days=days_ahead)
    return next_monday

def reset_changes_if_monday():
    """Сбрасывает изменения, если сегодня понедельник и сброс ещё не делали"""
    global changes
    
    today = datetime.date.today()
    if today.weekday() == 0:
        reset_key = f"reset_{today.isoformat()}"
        if reset_key not in changes:
            changes = {}
            changes[reset_key] = True
            return True
    return False

def apply_changes(day, lessons):
    """Применяет изменения к расписанию"""
    day_lower = day.lower()
    
    if day_lower in changes:
        for change in changes[day_lower]:
            parts = change.split(":")
            if len(parts) >= 2:
                try:
                    index = int(parts[0]) - 1
                    new_lesson = parts[1].strip()
                    if 0 <= index < len(lessons):
                        lessons[index] = new_lesson
                except:
                    pass
    return lessons

def parse_change_command(command):
    """Разбирает команду изменения расписания"""
    command = command.lower()
    
    found_day = None
    for day in weekdays:
        if day in command:
            found_day = day
            break
    
    if not found_day:
        return None
    
    if "замени" in command and " на " in command:
        parts = command.split("замени")[1].split(" на ")
        if len(parts) >= 2:
            old_lesson = parts[0].strip()
            new_lesson_part = parts[1].strip()
            if found_day in new_lesson_part:
                new_lesson = new_lesson_part.replace(found_day, "").strip()
            else:
                new_lesson = new_lesson_part
            
            return {
                "day": found_day,
                "old": old_lesson,
                "new": new_lesson
            }
    
    return None

@app.route('/', methods=['POST'])
def webhook():
    """Основной обработчик запросов от Маруси"""
    
    req = request.json
    
    if not req:
        return jsonify({
            "response": {
                "text": "Произошла ошибка",
                "end_session": True
            },
            "version": "1.0"
        })
    
    reset_changes_if_monday()
    
    command = req.get("request", {}).get("command", "").lower()
    session = req.get("session", {})
    new_session = session.get("new", False)
    
    if new_session:
        response_text = "Привет! Я твой помощник с расписанием уроков. Спроси меня: 'расписание на сегодня', 'что завтра' или 'уроки на понедельник'."
        
        return jsonify({
            "response": {
                "text": response_text,
                "end_session": False,
                "buttons": [
                    {"title": "Сегодня", "hide": True},
                    {"title": "Завтра", "hide": True},
                    {"title": "Понедельник", "hide": True}
                ]
            },
            "session": session,
            "version": "1.0"
        })
    
    change_cmd = parse_change_command(command)
    if change_cmd:
        day = change_cmd["day"]
        old = change_cmd["old"]
        new = change_cmd["new"]
        
        lessons = schedule.get(day, []).copy()
        found = False
        for i, lesson in enumerate(lessons):
            if old in lesson.lower():
                if day not in changes:
                    changes[day] = []
                changes[day].append(f"{i+1}:{new}")
                found = True
                response_text = f"Хорошо, заменила '{old}' на '{new}' в {day}. Изменение будет действовать до следующего понедельника."
                break
        
        if not found:
            response_text = f"Не нашла урок '{old}' в расписании на {day}."
        
        return jsonify({
            "response": {
                "text": response_text,
                "end_session": False
            },
            "session": session,
            "version": "1.0"
        })
    
    day_to_show = None
    
    if "сегодня" in command or "сейчас" in command:
        day_to_show = get_current_day()
        day_text = "сегодня"
    elif "завтра" in command:
        day_to_show = get_tomorrow()
        day_text = "завтра"
    elif "послезавтра" in command:
        day_to_show = get_day_after_tomorrow()
        day_text = "послезавтра"
    else:
        for day in weekdays:
            if day in command:
                day_to_show = day
                day_text = f"в {day}"
                break
    
    if not day_to_show:
        response_text = "Извини, я не поняла, на какой день нужно расписание. Спроси, например, 'расписание на понедельник' или 'что завтра'."
    else:
        lessons = schedule.get(day_to_show, [])
        
        if day_to_show in changes:
            lessons = apply_changes(day_to_show, lessons.copy())
        
        if lessons:
            lesson_texts = []
            for lesson in lessons:
                lesson_texts.append(lesson)
            response_text = f"Расписание {day_text}:\n" + "\n".join(lesson_texts)
        else:
            response_text = f"В {day_text} уроков нет."
    
    return jsonify({
        "response": {
            "text": response_text,
            "end_session": False,
            "buttons": [
                {"title": "Сегодня", "hide": True},
                {"title": "Завтра", "hide": True},
                {"title": "Понедельник", "hide": True}
            ]
        },
        "session": session,
        "version": "1.0"
    })

@app.route('/', methods=['GET'])
def hello():
    return "Навык работает!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)