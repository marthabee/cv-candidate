use('talentmatch');

db.createCollection("users");
db.users.insertOne({
    email: "candidate@example.com",
    password: "12345/",
    user_type: "candidate"
  });
  
  db.users.insertOne({
    email: "company@example.com",
    password: "12345",
    user_type: "company"
  });


db.createCollection("candidates");
db.candidates.insertOne({
    name: "John Doe",
    email: "john.doe@example.com",
    skills: ["python", "flask", "mongodb"],
    resume_id: "1"
  });
  
  db.candidates.insertOne({
    name: "Jane Smith",
    email: "jane.smith@example.com",
    skills: ["javascript", "nodejs", "react"],
    resume_id: "2"
  });