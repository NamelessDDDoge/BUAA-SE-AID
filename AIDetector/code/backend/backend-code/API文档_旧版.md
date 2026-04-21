### **API文档结构：**

#### **1. 用户相关接口**
   - 用户注册
   - 用户登录
   - 用户登出
   - 用户信息更新

#### **2. 图像上传接口**
   - 上传图像（或PDF文件）
   - 获取上传图像的详情

#### **3. AI检测结果接口**
   - 获取图像的AI检测结果

#### **4. 人工审查接口**
   - 提交人工审查
   - 获取人工审查结果

#### **5. 反馈接口**
   - 提交反馈（点赞/评论）
   - 获取反馈列表

---

### **1. 用户相关接口**

#### **1.1 用户注册**
   **URL**: `/api/register/`  
   **方法**: `POST`  
   **请求体**:
   ```json
   {
     "username": "string",
     "email": "string",
     "password": "string"
   }
   ```

   **响应**:
   ```json
   {
     "message": "User created successfully",
     "user_id": "integer"
   }
   ```

#### **1.2 用户登录**
   **URL**: `/api/login/`  
   **方法**: `POST`  
   **请求体**:
   ```json
   {
     "email": "string",
     "password": "string"
   }
   ```

   **响应**:
   ```json
   {
     "token": "string",
     "message": "Login successful"
   }
   ```

#### **1.3 用户登出**
   **URL**: `/api/logout/`  
   **方法**: `POST`  
   **请求体**:
   ```json
   {
     "token": "string"
   }
   ```

   **响应**:
   ```json
   {
     "message": "Logout successful"
   }
   ```

#### **1.4 更新用户信息**
   **URL**: `/api/user/{user_id}/update/`  
   **方法**: `PUT`  
   **请求体**:
   ```json
   {
     "username": "string",
     "email": "string",
     "password": "string"
   }
   ```

   **响应**:
   ```json
   {
     "message": "User information updated successfully"
   }
   ```

---

### **2. 图像上传接口**

#### **2.1 上传图像（或PDF文件）**
   **URL**: `/api/upload/`  
   **方法**: `POST`  
   **请求体**:
   - **Content-Type**: `multipart/form-data`
   - **字段**: `file` (上传文件，支持图像或PDF)

   **响应**:
   ```json
   {
     "message": "File uploaded successfully",
     "image_id": "integer",
     "file_url": "string"
   }
   ```

#### **2.2 获取上传图像详情**
   **URL**: `/api/upload/{image_id}/`  
   **方法**: `GET`  
   **响应**:
   ```json
   {
     "image_id": "integer",
     "user_id": "integer",
     "file_name": "string",
     "file_url": "string",
     "upload_time": "timestamp",
     "is_pdf": "boolean",
     "extracted_images": ["image1_url", "image2_url"]
   }
   ```

---

### **3. AI检测结果接口**

#### **3.1 获取AI检测结果**
   **URL**: `/api/detection/{image_id}/`  
   **方法**: `GET`  
   **响应**:
   ```json
   {
     "image_id": "integer",
     "is_fake": "boolean",
     "confidence_score": "float",
     "detection_time": "timestamp"
   }
   ```

---

### **4. 人工审查接口**

#### **4.1 提交人工审查**
   **URL**: `/api/review/`  
   **方法**: `POST`  
   **请求体**:
   ```json
   {
     "detection_result_id": "integer",
     "score": "integer",
     "comment": "string"
   }
   ```

   **响应**:
   ```json
   {
     "message": "Review submitted successfully",
     "review_id": "integer"
   }
   ```

#### **4.2 获取人工审查结果**
   **URL**: `/api/review/{review_id}/`  
   **方法**: `GET`  
   **响应**:
   ```json
   {
     "review_id": "integer",
     "detection_result_id": "integer",
     "reviewer_id": "integer",
     "score": "integer",
     "comment": "string",
     "review_time": "timestamp"
   }
   ```

---

### **5. 反馈接口**

#### **5.1 提交反馈（点赞/评论）**
   **URL**: `/api/feedback/`  
   **方法**: `POST`  
   **请求体**:
   ```json
   {
     "manual_review_id": "integer",
     "is_like": "boolean",
     "comment": "string"
   }
   ```

   **响应**:
   ```json
   {
     "message": "Feedback submitted successfully",
     "feedback_id": "integer"
   }
   ```

#### **5.2 获取反馈列表**
   **URL**: `/api/feedback/{manual_review_id}/`  
   **方法**: `GET`  
   **响应**:
   ```json
   {
     "manual_review_id": "integer",
     "feedbacks": [
       {
         "feedback_id": "integer",
         "user_id": "integer",
         "is_like": "boolean",
         "comment": "string",
         "feedback_time": "timestamp"
       },
       ...
     ]
   }
   ```

