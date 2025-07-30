Foodgram - это веб-приложение, которое позволяет пользователям делиться рецептами, сохранять понравившиеся рецепты, подписываться на других авторов, добавлять ингредиенты из рецептов в список покупок и скачивать этот список. Приложение предоставляет удобный интерфейс для поиска блюд по тегам и управления личными коллекциями рецептов.

https://foodgramgram.ddns.net/

Автор: Фолингер Артем Дениславович, https://github.com/amok-a

Стек:
*   Backend: Python 3, Django, Django REST Framework, Djoser, drf-spectacular
*   Frontend: JavaScript, React
*   Database: PostgreSQL
*   Containerization: Docker, Docker Compose
*   Web Server: Nginx, Gunicorn
*   API Documentation: Swagger, ReDoc

CI/CD

Развертывание проекта осуществляется с помощью GitHub Actions. Workflow определен в `.github/workflows/main.yml` и включает следующие этапы:
1.  Запуск тестов.
2.  Сборка и пуш Docker образов в Docker Hub.
3.  Деплой на удаленный сервер.


Локальное развертывание с Docker
Клонирование репозитория

git clone https://github.com/amok-a/foodgram
cd foodgram
cd infra
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --noinput
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /static/
docker compose exec backend python manage.py load_ingredients

Без Docker
git clone https://github.com/amok-a/foodgram
cd foodgram
cd backend
python3 -m venv venv
. venv/scripts/activate
pip install -r requirements.txt
python manage.py load_ingredients
python manage.py runserver
cd ../frontend
npm install
npm start

Документация для локального изучения
http://127.0.0.1:8000/api/docs/