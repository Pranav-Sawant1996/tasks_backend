from flask import Flask, render_template, request, jsonify
import mysql.connector
import bcrypt
import datetime
import os
from dotenv import load_dotenv
import requests
from sklearn.tree import DecisionTreeClassifier


app = Flask(__name__)
load_dotenv()
connection = mysql.connector.connect(
    host="localhost",
    user= os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD"),
    database=os.getenv("DATABASE_NAME")
    )

cursor = connection.cursor()

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/yiyanghkust/finbert-tone"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

def analyze_text_with_huggingface(text):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text}
    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error Hugging Face API: {e}")
        return {"error": "Failed to analyze text"}


X_train = [
    [2, 3, 2],  # Task 1 days, complexity, estimated time
    [10, 2, 10],  # Task 2
    [1, 1, 1],  # Task 3
    [5, 2, 4],  # Task 4
]

# Corresponding labels (y_train)
y_train = [1, 2, 3, 2]  # 1 = High, 2 = Moderate, 3 = Low

# Train the model
model = DecisionTreeClassifier()
model.fit(X_train, y_train)

def predict_priority(days_to_deadline, complexity, estimated_time):
    prediction = model.predict([[days_to_deadline, complexity, estimated_time]])
    return prediction[0] 

@app.route('/prioritize-tasks', methods=["POST"])
def prioritize_tasks():
    if request.method == "POST":
        data = request.json
        user_id = data["user_id"]
        try:
            cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (user_id,))
            tasks = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # print('tasks',tasks)
            taskList=[]
            for record in tasks:
                record_with_columns = dict(zip(column_names, record))
                deadline = record_with_columns["deadline"]
                if isinstance(deadline, datetime.date):
                    deadline = datetime.datetime.combine(deadline, datetime.datetime.min.time())
                complexity = record_with_columns["complexity"]
                estimated_time = record_with_columns["estimated_time"]
                predicted_priority = predict_priority((deadline - datetime.datetime.now()).days, complexity, estimated_time)
                record_with_columns["predicted_priority"] = int(predicted_priority)

                taskList.append(record_with_columns)

            sorted_tasks = sorted(taskList, key=lambda x: x["predicted_priority"], reverse=True)
            topTasks=[]
            for i in range(3):
                topTasks.append(sorted_tasks[i])
                # print("ttttt",topTasks)
            return jsonify({"success": True, "prioritizedTasks": topTasks})
        except Exception as e:
            print("Prioritize error:", e)
            return jsonify({"success": False, "message": "Failed to prioritize tasks"})

@app.route('/sign_up', methods=["POST","GET"])
def sign_up():
    data = request.json
    print("ddddd",data)
    if request.method=="POST":
        first_name=data["firstname"]
        last_name=data["lastname"]
        email=data["email"]
        password=data["password"]
        username=data["username"]
        try:
            bytes = password.encode('utf-8') 
            # generating the salt 
            salt = bcrypt.gensalt() 
            hash_password = bcrypt.hashpw(bytes, salt) 

            cursor.execute("INSERT INTO users (firstname,lastname,username,email,password_hash) VALUES (%s,%s,%s,%s,%s)",(first_name,last_name,username,email,hash_password,))
            connection.commit()
            cursor.execute("SELECT * FROM users")
            info=cursor.fetchall()
            print("iiii",info)
            return jsonify({"success": True})
        except:
            return jsonify({"success": False, "message": "sign-up not successfull"})

@app.route('/sign_in', methods=["POST","GET"])
def sign_in():
    if request.method=="POST":
        data = request.json  
        print("ddd",data)
        username = data["username"]
        password = data["password"]
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        enc_password=cursor.fetchone()
        if enc_password == None:
                return jsonify({"success": False, "message": "User not found"})
        hash = enc_password[0].encode('utf-8') 
        # encoding user password 
        userBytes = password.encode('utf-8') 
        # checking password 
        result = bcrypt.checkpw(userBytes, hash) 

        if result:
            print("Sign-in successful!")
            cursor.execute("SELECT id,firstname,lastname,username,email FROM users WHERE username = %s", (username,))
            userDetails=cursor.fetchone()
            user_info = {
                "id": userDetails[0],
                "firstname": userDetails[1],
                "lastname": userDetails[2],
                "username": userDetails[3],
                "email": userDetails[4]
            }
            return jsonify({"success": True, "userDetails": user_info})
        else:
            print("Incorrect password. Please try again.")
            return jsonify({"success": False, "message": "Incorrect password"})

@app.route('/add-task', methods=["POST","GET"])
def add_task():
    if request.method=="POST":
        data = request.json  
        print("aaa0",data)
        task_title = data['title']
        description=data['task_description']
        priority=data['priority']
        convert_date=datetime.datetime.strptime(data['deadline'], "%Y-%m-%d")
        deadline=convert_date
        status=data['status']
        estimated_time=data['estimated_time']
        user_id=data['user_id']
        complexity=data['complexity']
        print("ddd",data)
        try:
            cursor.execute("INSERT INTO tasks (task_title, description, priority, deadline, status,estimated_time, user_id, complexity) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(task_title,description,priority,deadline,status,estimated_time, user_id,complexity))
            connection.commit()
            return jsonify({"success": True, "message": "Task added successfully"})
        except Exception as e:
            print(f"Error occurred: {e}")
            return jsonify({"success": False, "message": "task not added"})
        
@app.route('/get-task', methods=["POST","GET"])
def get_task():
    if request.method=="POST":
        user_id = request.json  
        # print("uuuuuuu",user_id)
        try:
            cursor.execute('SELECT * FROM tasks WHERE user_id = %s',(user_id,))
            tasks=cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # print('tasks',tasks)
            taskList=[]
            for record in tasks:
                record_with_columns = dict(zip(column_names, record))
                taskList.append(record_with_columns)
            return jsonify({"success": True, "tasks":taskList})
        except:
            return jsonify({"success": False})

@app.route('/delete-task', methods=["POST","GET"])
def delete_task():
    if request.method=="POST":
        data = request.json 
        id = data["id"]
        # print("dddddd",id)
        try:
            cursor.execute('SELECT id FROM tasks WHERE id=%s', (id,))
            task=cursor.fetchone()
            if task == None:
                return jsonify({"success": False, "message": "task not found"})
            print("task", task)
            cursor.execute('DELETE FROM tasks WHERE id=%s', (id,))
            connection.commit()
            # print("delete")
            return jsonify({"success": True, "message": "Task deleted"})
        except Exception as e:
            # print("rrrrrr",e)
            return jsonify({"success": False, "message": "Task not deleted"})
        
@app.route('/update-task', methods=["POST","GET"])
def update_task():
    if request.method=="POST":
        data = request.json 
        print('uuuuuu',data)
        task_title = data['title']
        description=data['task_description']
        priority=data['priority']
        convert_date=datetime.datetime.strptime(data['deadline'], "%Y-%m-%d")
        deadline=convert_date
        status=data['status']
        estimated_time=data['estimated_time']
        # user_id=data['user_id']
        id=data['id']
        complexity=data['complexity']
        try:
            cursor.execute('SELECT id FROM tasks WHERE id=%s', (id,))
            task=cursor.fetchone()
            if task == None:
                return jsonify({"success": False, "message": "task not found"})
            
            cursor.execute('UPDATE tasks SET task_title=%s, description=%s, priority=%s, deadline=%s, status=%s, estimated_time=%s,complexity=%s  WHERE id=%s',(task_title,description,priority,deadline,status,estimated_time,id,complexity,))
            connection.commit()
            return jsonify({"success": True, "message": "task updated"})
        except Exception as e:
            print("rrrrrr",e)
            return jsonify({"success": False, "message": "task not updated"})

@app.route('/overdue-task', methods=["POST","GET"])
def overdue_task():
    if request.method=="POST":
        data = request.json 
        user_id=data['user_id']
        # print('uuuuu',data)
        try:
            cursor.execute('SELECT * FROM tasks WHERE user_id = %s AND deadline < NOW() AND status != "Completed"',(user_id,))
            overdueTasks=cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # print('tasks',tasks)
            overdueTaskList=[]
            for record in overdueTasks:
                record_with_columns = dict(zip(column_names, record))
                overdueTaskList.append(record_with_columns)
            
            cursor.execute('SELECT * FROM tasks WHERE user_id = %s AND deadline >= NOW() AND status != "Completed"',(user_id,))
            upcomimgTasks=cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # print('tasks',tasks)
            upcomingTaskList=[]
            for record in upcomimgTasks:
                record_with_columns = dict(zip(column_names, record))
                upcomingTaskList.append(record_with_columns)
            return jsonify({"success": True, "overdueTasks":overdueTaskList, "upcomimgTasks":upcomingTaskList})
        except Exception as e:
            print("overdue err",e)
            return jsonify({"success": False})

@app.route('/filter-task', methods=["POST","GET"])
def filter_task():
    if request.method=="POST":
        data = request.json 
        user_id=data['user_id']
        priority=data['priority']
        status=data['status']
        print('fffff',data)
        try:
            query = "SELECT * FROM tasks WHERE user_id = %s"
            params = [user_id]
            if priority:
                query += " AND priority = %s"
                params.append(priority)

            if status:
                query += " AND status = %s"
                params.append(status)

            cursor.execute(query,params)
            Tasks=cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            filterredTaskList=[]
            for record in Tasks:
                record_with_columns = dict(zip(column_names, record))
                filterredTaskList.append(record_with_columns)
            return jsonify({"success": True, "filteredTasks":filterredTaskList })
        except Exception as e:
            print("filtered err",e)
            return jsonify({"success": False})
        
@app.route('/analyze-text', methods=["POST"])
def analyze_text():
    if request.method == "POST":
        data = request.json
        text=data['text']
        try:
            result = analyze_text_with_huggingface(text)
            # print("ssss",result)
            sorted_analysis = sorted(result[0], key=lambda x: x["score"], reverse=True)
            sentiment = sorted_analysis[0] 
            # print("ssss",sentiment)
            return jsonify({"success": True, "analysis": sentiment})
        except Exception as e:
            print("analyze err",e)
            return jsonify({"success": False})

if __name__ == '__main__':
    app.run(debug=True,port=3003)

cursor.close()
connection.close()