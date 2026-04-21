### **API文档结构：**

#### **1. 用户相关接口**
   - 用户注册
   - 用户登录
   - 用户登出
   - 用户信息更新
   - 获取用户详细信息
   - 刷新用户token
   - 更新用户头像
   - 忘记密码
   - 请求重置邮件

#### **2. 图像上传接口**
   - 上传文件
   - 获取上传文件的详情
   - 提交检测任务
   - 获取文件提取的图像列表

#### **3. AI检测结果接口**
   - 获取图像的AI检测结果
   - 获取检测任务状态
   - 获取用户的所有任务

#### **4. 人工审查接口**
   - 提交人工审查
   - 获取人工审查结果
   - 申请人工审查
   - 获取人工审查申请状态

#### **5. 反馈接口**
   - 提交反馈（点赞/评论）
   - 获取反馈列表

#### **6. 日志接口**
   - 获取操作日志

#### **7. 组织接口**



---

## **1. 用户相关接口**

---

### **1.1 用户注册**
- **URL**: `/api/register/`
- **方法**: `POST`
- **请求体**:
```json
{
  "username": "string",        // 用户名，必填
  "email": "string",           // 用户的电子邮件，必填
  "password": "string",        // 用户的密码，必填
  "invitation_code": "string"  // 邀请码，必填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "User created successfully",  // 用户创建成功的消息
      "user_id": "integer"                    // 新创建用户的唯一ID
    }
    ```
    - **状态码**: `201 Created`

  - **失败**（如缺少必填字段或字段格式不正确）:
    ```json
    {
      "username": ["This field is required."],  // 错误信息
      "email": ["This field is required."],
      "password": ["This field is required."],
      "invitation_code": ["Invalid or expired invitation code."]
    }
    ```
    - **状态码**: `400 Bad Request`

---

### **1.2 用户登录**
- **URL**: `/api/login/`
- **方法**: `POST`
- **请求体**:
```json
{
  "email": "string",          // 用户的电子邮件地址，必填
  "password": "string",       // 用户的密码，必填
  "role": "string"            // 用户选择的角色，必填，选项：'publisher', 'reviewer'
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "access": "string",            // 访问 token，用于后续授权
      "refresh": "string",           // 刷新 token，用于获取新的 access token
      "role": "string",              // 用户的角色，'publisher' 或 'reviewer'
      "profile": "string",           // 用户的简介
      "avatar": "string",            // 用户头像的 URL
      "organization": "string|null", // 用户所属组织名称，如无组织则为 null
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如电子邮件或密码不正确）:
    ```json
    {
      "message": "Invalid credentials"  // 错误消息，表示凭证无效
    }
    ```
    - **状态码**: `401 Unauthorized`

  - **失败**（如果角色不匹配）:
    ```json
    {
      "message": "Invalid role. User is not a publisher."  // 错误消息，表示角色不匹配
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如请求数据格式不正确）:
    ```json
    {
      "email": ["This field is required."],        // 错误消息，表示缺少 email 字段
      "password": ["This field is required."],     // 错误消息，表示缺少 password 字段
      "role": ["This field is required."]          // 错误消息，表示缺少 role 字段
    }
    ```
    - **状态码**: `400 Bad Request`


---

### **1.3 用户登出**
- **URL**: `/api/logout/`
- **方法**: `POST`
- **请求体**:
```json
{
  "refresh": "string"  // 用户的 refresh token，必填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "Logout successful"  // 登出成功消息
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如缺少 refresh token）:
    ```json
    {
      "message": "Refresh token missing"  // 错误消息
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如无效的 token）:
    ```json
    {
      "message": "Token error: <error details>"  // 错误消息
    }
    ```
    - **状态码**: `400 Bad Request`

---

### **1.4 更新用户信息**
- **URL**: `/api/user/update/`
- **方法**: `PUT`
- **请求体**:
```json
{
  "username": "string",    // 用户名，选填
  "email": "string",       // 用户的电子邮件，选填
  "role": "string",        // 用户角色，选填，默认为 "reviewer"；选项：'publisher', 'reviewer'
  "profile": "string",     // 用户简介，选填
  "avatar": "file"         // 用户头像，选填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "User information updated successfully"  // 更新成功的消息
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如缺少认证 token 或请求数据格式不正确）:
    ```json
    {
      "message": "Error message details"  // 错误详情
    }
    ```
    - **状态码**: `400 Bad Request` 或 `401 Unauthorized`

---

### **1.5 获取用户详细信息**
- **URL**: `/api/user/details/`
- **方法**: `GET`
- **请求体**: 无
- **请求头**:
  - `Authorization: Bearer <access_token>`  // 用户的访问 token，必填

- **响应**:
  - **成功**:
    ```json
    {
      "username": "string",    // 用户名
      "email": "string",       // 用户的电子邮件
      "role": "string",        // 用户角色
      "profile": "string",     // 用户简介
      "avatar": "string",      // 用户头像的 URL
      "permission": "string",       // 用户权限（或权限列表）
      "organization": "int",        // 组织 ID，若无组织则为 null
      "organization_name": "string" // 组织名称，若无组织则为 null
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如无效或过期的 token）:
    ```json
    {
      "message": "Authentication credentials were not provided."  // 错误消息
    }
    ```
    - **状态码**: `401 Unauthorized`

---

### **1.6 刷新用户token**
- **URL**: `/api/token/refresh/`
- **方法**: `POST`
- **请求体**:
```json
{
  "refresh": "string"  // 用户的 refresh token，必填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "access": "string"  // 新的 access token
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如缺少 refresh token）:
    ```json
    {
      "message": "Refresh token is required"  // 错误消息
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如无效的 refresh token）:
    ```json
    {
      "message": "Token error: <error details>"  // 错误消息
    }
    ```
    - **状态码**: `400 Bad Request`

---

### **1.7 更新用户头像**
- **URL**: `/api/user/avatar/`
- **方法**: `PUT`
- **请求体**:
  - 使用 `multipart/form-data` 格式上传图片文件。
  - 请求体应包含一个字段 `avatar`，它是一个图片文件（如 PNG, JPG 等格式）。

#### 示例请求：
```bash
PUT /api/user/avatar/
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

**请求体**（示例）:
```json
{
  "avatar": "file"  // 用户上传的头像文件
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "Avatar updated successfully"  // 更新头像成功的消息
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如缺少头像文件或文件格式错误）:
    ```json
    {
      "avatar": ["This field is required."]  // 错误信息，表示缺少头像文件
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如无效或过期的 token）:
    ```json
    {
      "message": "Authentication credentials were not provided."  // 错误信息，表示缺少认证
    }
    ```
    - **状态码**: `401 Unauthorized`


---

### **1.8 密码重置请求**
- **URL**: `/api/password-reset/`
- **方法**: `POST`
- **请求体**:
```json
{
  "email": "string"  // 用户注册时的电子邮件地址，必填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "Password reset email sent."  // 成功发送密码重置邮件
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如邮箱未注册）:
    ```json
    {
      "message": "Email not found."  // 错误消息，邮箱未找到
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如果请求数据不符合要求）:
    ```json
    {
      "email": ["This field is required."]  // 错误消息，表示缺少email字段
    }
    ```
    - **状态码**: `400 Bad Request`

#### **1.8.1 说明**
- **邮箱格式检查**: 请求体中的 `email` 字段必须是有效的邮箱地址。
- **发送验证码**: 系统将生成一个 6 位的验证码并发送到用户提供的电子邮件地址。
- **验证码有效期**: 生成的验证码有效期为 10 分钟，超过此时间需要重新请求验证码。

---

### **1.9 密码重置确认**
- **URL**: `/api/password-reset/confirm/`
- **方法**: `POST`
- **请求体**:
```json
{
  "email": "string",            // 用户注册时的电子邮件地址，必填
  "reset_code": "string",       // 用户收到的验证码，必填
  "new_password": "string"      // 用户输入的新密码，必填
}
```

- **响应**:
  - **成功**:
    ```json
    {
      "message": "Password has been reset successfully."  // 密码重置成功的消息
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（如验证码不正确或已过期）:
    ```json
    {
      "message": "Invalid or expired reset code."  // 错误消息，表示验证码无效或已过期
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如邮箱地址无效）:
    ```json
    {
      "message": "Invalid email address."  // 错误消息，表示邮箱地址无效
    }
    ```
    - **状态码**: `400 Bad Request`

  - **失败**（如请求数据不符合要求）:
    ```json
    {
      "reset_code": ["This field is required."],  // 错误消息，表示缺少验证码
      "new_password": ["This field is required."]  // 错误消息，表示缺少新密码
    }
    ```
    - **状态码**: `400 Bad Request`

#### **1.9.1 说明**
- **验证码验证**: 该接口验证用户输入的验证码与系统生成的验证码是否匹配，并检查验证码是否过期。
- **密码更新**: 如果验证码有效且未过期，系统将允许用户重置密码，并清除验证码及其过期时间。

---

### 1.10 获取用户操作日志
- **URL**: `/user_action_log/`
- **方法**: `GET`
- **权限**: 需要用户认证（`IsAuthenticated`）
- **参数**:

| 参数名         | 类型   | 默认值 | 描述                             |
|----------------|--------|--------|----------------------------------|
| `page`         | int    | 1      | 当前页码                         |
| `page_size`    | int    | 10     | 每页显示的日志条数               |
| `publisher`    | string | ''     | 出版社名称，用于筛选日志记录     |
| `status`       | string | ''     | 任务状态（`completed` 或 `pending`），用于筛选日志记录 |
| `startTime`    | string | None   | 操作时间筛选（开始时间，格式：YYYY-MM-DD HH:MM:SS） |
| `endTime`      | string | None   | 操作时间筛选（结束时间，格式：YYYY-MM-DD HH:MM:SS） |

- **返回**: 用户操作日志记录，包括操作时间、操作用户、操作类型、相关模型名称和相关ID。

```json
{
    "logs": [
        {
            "id": 1,
            "user": "username1",
            "operation_type": "create",
            "related_model": "DetectionTask",
            "related_id": 101,
            "operation_time": "2023-10-01 12:34:56"
        },
        {
            "id": 2,
            "user": "username2",
            "operation_type": "update",
            "related_model": "User",
            "related_id": 202,
            "operation_time": "2023-10-02 13:45:07"
        }
    ],
    "current_page": 1,
    "total_pages": 5,
    "total_logs": 50,
    "has_next": true,
    "has_previous": false
}
```

---

### **1.11 获取任务汇总**

* **URL**: `/api/task-summary/`

* **方法**: `GET`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**: 无

* **响应**:

  * **成功**（状态码 `200 OK`）

    ```json
    {
      "total_task_count": 100,           // 总任务数
      "completed_task_count": 80,        // 已完成任务数
      "recent_task_count": 20,           // 最近 30 天内的任务数
      "recent_tasks": [                  // 最近 30 天的任务详情列表
        {
          "task_id": 123,                // 任务 ID
          "task_name": "检测任务 A",      // 任务名称
          "status": "completed",         // 任务状态
          "upload_time": "2025-05-01T12:34:56Z",     // 上传时间，ISO 8601 格式
          "completion_time": "2025-05-02T15:20:30Z"  // 完成时间，ISO 8601 格式
        },
        {
          "task_id": 124,
          "task_name": "检测任务 B",
          "status": "pending",
          "upload_time": "2025-05-15T09:10:11Z",
          "completion_time": null
        }
        // ……
      ]
    }
    ```

  * **失败**

    * **未认证或 Token 无效**（状态码 `401 Unauthorized`）

      ```json
      {
        "detail": "Authentication credentials were not provided."
      }
      ```


---

### **1.12 获取组织使用情况**

* **URL**: `/api/organization/usage/`

* **方法**: `GET`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**: 无

* **响应**:

  * **成功**（状态码 `200 OK`）

    ```json
    {
      "remaining_non_llm_uses": 100,   // 组织剩余的非 LLM 调用次数
      "remaining_llm_uses": 50         // 组织剩余的 LLM 调用次数
    }
    ```

  * **失败**

    * **未认证或 Token 无效**（状态码 `401 Unauthorized`）

      ```json
      {
        "detail": "Authentication credentials were not provided."
      }
      ```

---

### **1.13 下载人工审核报告**

* **URL**: `/api/manual-review/{review_id}/report/`

* **方法**: `GET`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**: 无

* **响应**:

  * **成功**（状态码 `200 OK`）
    返回一个 ZIP 文件 `reports.zip`，包含两个 PDF 报告：

    * `task_{task_id}_report.pdf`：AI 检测结果报告
    * `manual_report.pdf`：人工审核结果报告

    ```http
    Content-Type: application/zip
    Content-Disposition: attachment; filename="reports.zip"
    ```

  * **失败**

    * **找不到任务或无权限**（状态码 `404 Not Found`）

      ```json
      {
        "detail": "Image or task not found, or permission denied."
      }
      ```
    * **检测结果异常**（状态码 `500 Internal Server Error`）

      ```json
      {
        "detail": "Multiple detection results found for this image."
      }
      ```
    * **任务未完成**（状态码 `400 Bad Request`）

      ```json
      {
        "detail": "Task not completed yet."
      }
      ```
    * **报告生成中**（状态码 `202 Accepted`）

      ```json
      {
        "detail": "Report is still being generated."
      }
      ```
    * **报告文件丢失**（状态码 `410 Gone`）

      ```json
      {
        "detail": "Report file missing: task_123_report.pdf"
      }
      ```



---

## **2. 图像上传接口**

### **2.1 上传文件**
- **URL**: `/api/upload/`
- **方法**: `POST`
- **请求体**:
  - `file`：上传的文件，可以是图片、PDF或ZIP文件。
- **响应**:
  - **成功**:
    ```json
    {
      "message": "File uploaded successfully",
      "file_id": "integer",
      "file_url": "string"
    }
    ```
    - **状态码**: `200 OK`
  
  - **失败**（例如无效文件类型）:
    ```json
    {
      "message": "Invalid file type."
    }
    ```
    - **状态码**: `400 Bad Request`
  
  - **失败**（无上传权限）:
    ```json
    {
      "错误": "该用户没有上传文件的权限"
    }
    ```
    - **状态码**: `403`

---

### **2.2 获取文件详细信息**
- **URL**: `/api/upload/{file_id}/`
- **方法**: `GET`
- **请求体**: 无
- **响应**:
  - **成功**:
    ```json
    {
      "file_id": "integer",
      "file_name": "string",
      "file_size": "integer",
      "file_url": "string",
      "upload_time": "string",
      "is_pdf": "boolean",
      "extracted_images": ["image_url_1", "image_url_2"]
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（文件未找到）:
    ```json
    {
      "message": "File not found"
    }
    ```
    - **状态码**: `404 Not Found`

---

### **2.3 获取提取的图片**

* **URL**: `/api/upload/{file_id}/extract_images/`

* **方法**: `GET`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**: 无

* **响应**:

  * **成功**（状态码 `200 OK`）

    ```json
    {
      "file_id": 1,                // 文件 ID
      "page": 1,                   // 当前页码
      "page_size": 10,             // 单页大小
      "total": 25,                 // 总图片数
      "images": [
        {
          "image_id": 100,             // 图片 ID
          "image_url": "string",       // 图片访问 URL
          "page_number": 2,            // 来自 PDF 时的页码，非 PDF 时为 null
          "extracted_from_pdf": true,  // 是否从 PDF 中提取
          "isDetect": false,           // 是否已做 AI 检测
          "isReview": false,           // 是否已做人工复核
          "isFake": null               // 假图判定结果：true/false，未判定时为 null
        },
        {
          "image_id": 101,
          "image_url": "string",
          "page_number": null,
          "extracted_from_pdf": false,
          "isDetect": true,
          "isReview": false,
          "isFake": null
        }
        // ……
      ]
    }
    ```

  * **失败**

    * **文件未找到**（状态码 `404 Not Found`）

      ```json
      {
        "message": "File not found"
      }
      ```


---

## **3. AI检测结果接口**

### **3.1 获取检测结果**
- **URL**: `/api/detection/{image_id}/`
- **方法**: `GET`
- **请求体**: 无
- **响应**:
  - **正在检测中**:
    ```json
    {
      "image_id": "integer",
      "status": "正在检测中",
      "message": "AI检测正在进行，请稍等"
    }
    ```
    - **状态码**: `200 OK`
  
  - **检测已完成**:
    ```json
    {
      "image_id": "integer",
      "status": "检测已完成",
      "is_fake": "boolean",
      "confidence_score": "float",
      "detection_time": "string"
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（检测结果未找到）:
    ```json
    {
      "message": "Detection result not found"
    }
    ```
    - **状态码**: `404 Not Found`

---

### **3.2 提交检测任务**

* **URL**: `/api/detection/submit/`

* **方法**: `POST`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**:

  ```json
  {
    "mode": 1,                   // 提交模式，必填；1=普通(non‑LLM)、2=加急(non‑LLM 高优先)、3=LLM（使用 LLM 并自动加急）
    "image_ids": [1,2,3],        // 图像的 ID 列表，必填
    "task_name": "string",       // 任务名称，可选，默认为 "New Detection Task"
    "cmd_block_size": 64,        // 可选，每批处理的块大小，默认为 64
    "urn_k": 0.3,                // 可选，URN 参数，默认为 0.3
    "if_use_llm": false          // 可选，是否使用 LLM 方法；当 mode=3 时强制为 true
  }
  ```

* **响应**:

  * **成功**（状态码 `200 OK`）

    ```json
    {
      "message": "Detection request submitted successfully",  // 提交成功消息
      "task_id": 123,                                        // 新创建任务的 ID
      "task_name": "My Detection Task"                       // 任务名称
    }
    ```

  * **失败**

    * **未提供图像 ID**（状态码 `400 Bad Request`）

      ```json
      {
        "message": "No image IDs provided"
      }
      ```

    * **无权限提交**（状态码 `403 Forbidden`）

      ```json
      {
        "错误": "该用户没有提交检测的权限"
      }
      ```

    * **未找到有效图像**（状态码 `404 Not Found`）

      ```json
      {
        "message": "No valid images found"
      }
      ```

    * **超出非 LLM 使用限额**（状态码 `400 Bad Request`）

      ```json
      {
        "message": "You have exceeded your non-LLM method usage limit for this week. Your organization can only submit  X  more images."
      }
      ```

    * **超出 LLM 使用限额**（状态码 `400 Bad Request`）

      ```json
      {
        "message": "You have exceeded your LLM method usage limit for this week. Your organization can only submit  Y  more images."
      }
      ```
---

### **3.3 获取检测任务状态**
- **URL**: `/api/detection-task/{task_id}/status/`
- **方法**: `GET`
- **请求体**: 无
- **响应**:
  - **成功**:
    ```json
    {
      "task_id": "integer",
      "task_name": "string",
      "status": "string",
      "upload_time": "string",
      "completion_time": "string",
      "detection_results": [
        {
          "image_id": "integer",
          "status": "string",
          "is_fake": "boolean",
          "confidence_score": "float",
          "detection_time": "string"
        }
      ]
    }
    ```
    - **状态码**: `200 OK`

  - **失败**（任务未找到）:
    ```json
    {
      "message": "Detection task not found"
    }
    ```
    - **状态码**: `404 Not Found`

### **3.4 获取用户的所有任务（分页）**
• URL: `/api/user-tasks/`

• 方法: `GET`

• 请求参数:

  • `page` (可选, 整数): 指定页码，默认为1

  • `page_size` (可选, 整数): 每页数量（1-100），默认为10

• 响应:

  • 成功 (状态码 200 OK):

    ```json
    {
      "page": 1,
      "page_size": 10,
      "total": 15,
      "tasks": [
        {
          "task_id": "integer",
          "task_name": "string",
          "status": "string",
          "upload_time": "string",
          "completion_time": "string"
        }
      ]
    }
    ```
    ◦ 当没有任务时仍返回200状态码，tasks为空数组，total为0


  • 失败:

    ◦ 无效分页参数（如超出有效页码）:
    
      ```json
      {
        "detail": "Invalid page."
      }
      ```
      ◦ 状态码: `404 Not Found`

---


### **3.5 获取任务下的所有检测结果**  

| | |
|---|---|
| **URL** | `/api/tasks/{task_id}/results/` |
| **Method** | `GET` |
| **Query Params** | `include_image` `0/1` 可选 – 如为 1/true，则在每条结果中额外返回 `image_url` |
| **Body** | – |

#### 成功 `200 OK`

```json
{
  "task_id": 8,
  "total_results": 3,
  "results": [
    {"result_id": 41, "image_url": "/media/extracted_images/xxx.png"},
    {"result_id": 42, "image_url": "/media/extracted_images/yyy.png"},
    {"result_id": 43, "image_url": "/media/extracted_images/zzz.png"}
  ]
}
```
*(当 `include_image` 为 0/未提供时，仅含 `result_id` 字段)*  

#### 失败

| 场景 | JSON | HTTP |
|------|------|------|
| 任务不存在或无权限 | `{"detail":"Task not found."}` | 404 |

---

### **3.5.1 获取任务下的所有检测为真的结果 (NEW)**  
| | |
|---|---|
| **URL** | `/api/tasks/<int:task_id>/fake_results/` |

其他内容同3.5

### **3.5.2 获取任务下的所有检测为假的结果 (NEW)**  
| | |
|---|---|
| **URL** | `/api/tasks/<int:task_id>/normal_results/` |

其他内容同3.5

--

### **3.6 获取单个检测结果详情**  

| | |
|---|---|
| **URL** | `/api/results/{result_id}/` |
| **Method** | `GET` |
| **Query Params** | <ul><li>`fields` – 逗号分隔列表，控制顶层返回字段。可选值：<br>`overall,llm,ela_image,exif,timestamps,image,sub_methods`。<br>缺省=全部。</li><li>`include_matrix` – `0/1` 可选。当为 1/true 且请求了 `sub_methods`，则在子方法里额外返回 `mask_matrix`（256×256 浮点数组）。</li></ul> |
| **Body** | – |

#### 典型返回

```json
{
  "result_id": 41,
  "overall": {
    "is_fake": false,
    "confidence_score": 0.93
  },
  "llm": "The image appears authentic.",
  "ela_image": "/media/ela_results/41.png",
  "exif": {
    "photoshop_edited": false,
    "time_modified": false
  },
  "timestamps": "2025-04-30T09:12:25Z",
  "image": "/media/extracted_images/41.png",
  "sub_methods": [
    {
      "method": "method1",
      "probability": 0.12,
      "mask_image": "/media/masks/41_m1.png",
      "mask_matrix": null           // 未请求 include_matrix
    },
    {
      "method": "big_model_method",
      "probability": 0.80,
      "mask_image": "/media/masks/41_big.png",
      "mask_matrix": null
    }
  ]
}
```

#### 仅返回总体结论 + 子方法（含矩阵）

```
GET /api/results/41/?fields=overall,sub_methods&include_matrix=1
```

返回中 `mask_matrix` 为 256×256 数组。

#### 错误

| 场景 | JSON | HTTP |
|------|------|------|
| 结果不存在/无权限 | `{"detail":"Not found."}` | 404 |

---


### **3.7 下载检测报告**

* **URL**: `/api/tasks/{task_id}/report/`

* **方法**: `GET`

* **请求头**:

  ```http
  Authorization: Bearer <access_token>   // 用户的访问 token，必填
  ```

* **请求体**: 无

* **响应**:

  * **成功**（状态码 `200 OK`）
    返回一个 PDF 文件，Content-Type 为 `application/pdf`，文件名为 `task_{task_id}_report.pdf`：

    ```http
    Content-Type: application/pdf
    Content-Disposition: attachment; filename="task_123_report.pdf"
    ```

  * **失败**

    * **任务不存在**（状态码 `404 Not Found`）

      ```json
      {
        "detail": "Task not found."
      }
      ```
    * **任务未完成**（状态码 `400 Bad Request`）

      ```json
      {
        "detail": "Task not completed yet."
      }
      ```
    * **报告生成中**（状态码 `202 Accepted`）

      ```json
      {
        "detail": "Report is still being generated."
      }
      ```
    * **报告文件丢失**（状态码 `410 Gone`）

      ```json
      {
        "detail": "Report file missing."
      }
      ```


---

### **3.8 获取用户任务近一个月任务统计信息**
• URL: `/api/task-summary/` 

• 方法: `GET`

• 权限: 需要认证（`IsAuthenticated`）

• 请求参数: 无

• 响应:


  #### 成功响应 (200 OK)
  ```json
  {
    "total_task_count": 15,
    "completed_task_count": 12,
    "recent_task_count": 5,
    "recent_tasks": [
      {
        "task_id": 123,
        "task_name": "图像检测任务",
        "status": "completed",
        "upload_time": "2023-10-05T14:30:00+08:00",
        "completion_time": "2023-10-05T15:12:00+08:00"
      }
    ]
  }
  ```

  #### 错误响应
  • 未认证 (401 Unauthorized):

  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```

字段说明


| 字段  | 类型    | 说明|
|------|------|------|
| total_task_count     | int   | 用户创建的所有任务总数（历史累计）                                         |
| completed_task_count | int   | 状态为 completed 的任务数量                                             |
| recent_task_count    | int   | 最近30天内上传的任务数量                                                 |
| recent_tasks         | array | 最近30天内上传的任务详情列表（按上传时间倒序）                                  |
|  task_id            | int   | 任务唯一标识符                                                           |
|  task_name          | string | 任务名称（用户创建时指定）                                                  |
|  status             | string | 任务状态（例如：pending/completed/failed）                                |
|  upload_time        | string | 任务创建时间（ISO 8601格式，带时区）                                        |
|  completion_time    | string | 任务完成时间（ISO 8601格式，带时区，未完成时为`null`）                          |

---

#### **接口示例**

```bash
# 获取任务 8 的结果列表并带原图
GET /api/tasks/8/results/?include_image=1

# 获取结果 41 全量信息 + mask 矩阵
GET /api/results/41/?include_matrix=1

# 仅要总体结论
GET /api/results/41/?fields=overall

# 下载任务 8 的检测报告
GET /api/tasks/8/report/
```

> 所有接口均需携带 **JWT Authorization** 头，示例中未展开。

## **4. 人工审查接口**


### 4.0  获取所有审核员 `GET /api/get_all_reviewers/`

| 查询参数 | 说明 |
|----------|------|
| `query`  | （可选）用户名前缀模糊匹配 |

```json
[
  {
    "id": 21,
    "username": "alice",
    "avatar": "https://…/avatars/21.png"
  }
]
```

---

### 4.1  查看 Publisher-Reviewer 关联  
`GET /api/publishers/{publisher_id}/reviewers/`

```json
{
  "publisher_id": 5,
  "reviewers": [
    { "id": 21, "username": "alice", "avatar": null },
    { "id": 34, "username": "bob",   "avatar": "…" }
  ]
}
```

---

### 4.2  创建审核申请（管理员审批）  
`POST /api/create_review_task_with_admin_check/`

| JSON 字段 | 类型 | 必填 | 说明 |
|-----------|------|------|------|
| `image_ids` | int[] | ✔ | 同一 DetectionTask 下待复核的图片 ID |
| `reviewers` | int[] | ✔ | 指定审核员 ID 列表 |
| `reason` | string | ✖ | 申请理由 |

成功 201 示例：

```json
{
  "message": "Review task created and sent to admin for approval",
  "review_request_id": 88
}
```

---

### 4.3  检测任务的人工审核完成度  
`GET /api/get_request_completion_status/{task_id}/`

```json
{
  "task_id": 12,
  "completion_percentage": 66.7
}
```

---

### 4.4  审核申请详情  
`GET /api/get_request_detail/{reviewRequest_id}/`

```json
{
  "image_ids": [101, 102, 103],
  "ai_detection_result": {
    "is_fake": true,
    "confidence_score": 0.92,
    "detection_time": "2025-04-28 10:32:11"
  },
  "status": { "done": 1, "process": 2 },
  "reviewers_results": [
    { "reviewer_id": 21, "score": 73 }
  ]
}
```

---

### 4.5  单图多审核员结论  
`GET /api/get_img_review_all/?review_request_id=&img_id=`

```json
{
  "reviewers_results": [
    { "id": 21, "username": "alice", "avatar": null, "result": false },
    { "id": 34, "username": "bob",   "avatar": "…",  "result": true }
  ]
}
```

---

### 4.6  单图单审核员 7 分项详情  
`GET /api/get_image_review/?review_request_id=&img_id=&reviewer_id=`

```json
{
  "scores":  [3, 2, 4, 1, 2, 1, 0],
  "reasons": [null, "对比度略高", null, …],
  "result":  true
}
```

---

### 4.7  Publisher 自己的所有审核申请（分页）  
`GET /api/get_publisher_review_tasks/`

| 查询 | 说明 |
|------|------|
| `status` | pending / in_progress / completed |
| `startTime` `endTime` | 申请时间范围 |
| `page` `page_size` | 分页 |

```json
{
  "tasks": [
    {
      "review_request_id": 88,
      "request_time": "2025-04-28 14:25:03",
      "status": "in_progress",
      "progress": "1/3"
    }
  ],
  "current_page": 1,
  "total_pages": 1,
  "total_count": 3
}
```

---

### 4.8  Reviewer 的任务列表（分页）  
`GET /api/get_reviewer_tasks/`

| 查询 | 说明 |
|------|------|
| `status` | pending / in_progress / completed |
| `query`  | 发布者用户名前缀 |
| `start_time` `end_time` | 申请时间范围 |
| `page` `page_size` | ≤ 100 |

返回：

```json
{
  "results": [
    {
      "maual_review_id": 55,
      "maual_review_time": "2025-04-29 09:10:41",
      "publisher_username": "publ1",
      "publisher_avatar": null,
      "image_count": 5,
      "status": "in_progress"
    }
  ],
  …
}
```

---

### 4.9  Reviewer 查看自己已评详情  
`GET /api/get_review_detail/{manual_review_id}/`

```json
{
  "image_urls": ["https://…/101.png", "https://…/102.png"],
  "ai_detection_result": {
    "is_fake": true,
    "confidence_score": 0.92,
    "detection_time": "2025-04-28 10:32:11"
  },
  "count": 2,
  "reviewers_results": [
    {
      "image_id": 101,
      "scores":  [3,2,4,1,2,1,0],
      "reasons": ["…", null, null, …],
      "result":  true
    }
  ]
}
```

---

### 4.10  Reviewer 提交/更新评分  
`POST /api/post_review/{manual_review_id}/`

```json
{
  "result": [
    {
      "img_id": 101,
      "score":  [3,2,4,1,2,1,0],
      "reason": ["…", null, null, …],
      "final":  true
    },
    ...
  ]
}
```

成功 201：

```json
{ "message": "Review submitted successfully" }
```

> ⚠️ 提交完毕后，接口会：  
> * 将当前 `ManualReview.status` 置为 `completed`  
> * 若该 `ReviewRequest` 下所有审核员已完成，则自动把 `ReviewRequest.status` 置为 `completed` 并写入 `review_end_time`.

---


## **5. 反馈接口**

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
       }
     ]
   }
   ```

---

## **6. 日志接口**

#### **6.1 获取操作日志**
   **URL**: `/api/logs/`  
   **方法**: `GET`  
   **响应**:
   ```json
   {
     "logs": [
       {
         "log_id": "integer",
         "user_id": "integer",
         "operation_type": "upload",
         "related_model": "FileManagement",
         "related_id": "integer",
         "operation_time": "timestamp"
       },
       ...
     ]
   }
   ```

   - 返回操作日志记录，包括操作时间、操作用户、操作类型、相关模型名称和相关ID。



## 7. 管理端接口

#### 1. 管理员仪表盘视图
- **URL**: `/admin_dashboard/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**:
  - 用户信息列表，包含用户ID、用户名、邮箱、角色和加入日期
  - 最近30天的任务统计，包括总任务数、已完成任务数、待处理任务数和进行中任务数

```json
{
  "users": [
    {
      "id": "用户ID",
      "username": "用户名",
      "email": "用户邮箱",
      "role": "用户角色",
      "date_joined": "YYYY-MM-DD HH:MM:SS"
    },
  ],
  "task_stats": {
    "total_tasks": "总任务数",
    "completed_tasks": "已完成任务数",
    "pending_tasks": "待处理任务数",
    "in_progress_tasks": "进行中任务数"
  }
}
```


#### 2. 用户权限管理视图
- **URL**: `/user_permission/<int:user_id>/`
- **方法**: `POST`
- **权限**: 需要管理员权限
- **参数**: 
  - `permission_name`: 权限名称
- **返回**:
  - 成功添加权限的消息或错误信息

```json
{
  "message": "Permission {permission_name} added to user {username}"
}
```


#### 3. 帖子举报处理视图
- **URL**: `/post_report/<int:post_id>/`
- **方法**: `POST`
- **权限**: 需要管理员权限
- **参数**:
  - `reason`: 举报原因（可选）
- **返回**:
  - 成功举报的消息或错误信息

```json
{
  "message": "Post {post_id} reported successfully",
  "report_id": "举报记录ID"
}
```


#### 4. 用户操作日志视图

- **URL**: `/user_action_log/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**: 用户操作日志记录，包括操作时间、操作用户、操作类型、相关模型名称和相关ID。
- **参数**:

| 参数名         | 类型   | 默认值 | 描述                             |
|----------------|--------|--------|----------------------------------|
| `page`         | int    | 1      | 当前页码                         |
| `page_size`    | int    | 10     | 每页显示的日志条数               |
| `query`        | string | ''     | 搜索前缀匹配用户名               |
| `role`         | string | ''     | 角色筛选                         |
| `operation_type` | string | ''     | 操作类型筛选                     |
| `startTime`    | string | None   | 操作时间筛选（开始时间，格式：YYYY-MM-DD HH:MM:SS） |
| `endTime`      | string | None   | 操作时间筛选（结束时间，格式：YYYY-MM-DD HH:MM:SS） |


```json
{
    "logs": [
        {
            "id": 1,
            "user": "username1",
            "operation_type": "create",
            "related_model": "DetectionTask",
            "related_id": 101,
            "operation_time": "2023-10-01 12:34:56"
        },
        {
            "id": 2,
            "user": "username2",
            "operation_type": "update",
            "related_model": "User",
            "related_id": 202,
            "operation_time": "2023-10-02 13:45:07"
        }
    ],
    "current_page": 1,
    "total_pages": 5,
    "total_logs": 50,
    "has_next": true,
    "has_previous": false
}
```

- **URL**: `/user_action_log/<int:log_id>/`
- **方法**: `DELETE`
- **权限**: 需要管理员权限
- **返回**:
  - 成功删除日志的消息或错误信息

```markdown
{
  "message": "Log {log_id} deleted successfully"
}
```


- **URL**: `/user_action_log/download/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**:
  - 下载的日志CSV文件

#### 5. 获取任务概览
- **URL**: `/get_task_summary/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**:
  - 总任务数、已完成任务数、最近30天的任务数及详细信息

```markdown
{
  "total_task_count": "总任务数",
  "completed_task_count": "已完成任务数",
  "recent_task_count": "最近30天任务数",
  "recent_tasks": [
    {
      "task_id": "任务ID",
      "task_name": "任务名称",
      "status": "任务状态",
      "upload_time": "YYYY-MM-DD HH:MM:SS",
      "completion_time": "YYYY-MM-DD HH:MM:SS"
    },
    ...
  ]
}
```


#### 6. 获取检测任务状态
- **URL**: `/get_detection_task_status/<int:task_id>/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**:
  - 指定任务的详细信息及检测结果

```markdown
{
  "task_id": "任务ID",
  "task_name": "任务名称",
  "status": "任务状态",
  "upload_time": "YYYY-MM-DD HH:MM:SS",
  "completion_time": "YYYY-MM-DD HH:MM:SS",
  "detection_results": [
    {
      "image_id": "图像ID",
      "status": "检测状态",
      "is_fake": "是否为假",
      "confidence_score": "置信度分数",
      "detection_time": "YYYY-MM-DD HH:MM:SS"
    },
    ...
  ]
}
```


#### 7. 获取所有用户任务
- **URL**: `/get_all_user_tasks/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **返回**:
  - 所有任务的简要信息

```markdown
{
  "tasks": [
    {
      "task_id": "任务ID",
      "task_name": "任务名称",
      "status": "任务状态",
      "upload_time": "YYYY-MM-DD HH:MM:SS",
      "completion_time": "YYYY-MM-DD HH:MM:SS"
    },
    ...
  ]
}
```


#### 8. 获取分页用户信息
- **URL**: `/get_users/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **参数**:

| 参数名         | 类型     | 默认值 | 描述                                                        |
|----------------|--------|--------|-----------------------------------------------------------|
| `query`        | string | ''     | 搜索前缀匹配用户名                                                 |
| `role`         | string | ''     | 角色筛选                                                      |
| `permission`   | int    | ''     | 权限筛选,四位分别代表：上传，提交，发布，审核(例如，publisher默认为1110，reviewer默认为1） |
| `startTime`    | string | None   | 注册时间筛选（开始时间，格式：YYYY-MM-DD HH:MM:SS）                       |
| `endTime`      | string | None   | 注册时间筛选（结束时间，格式：YYYY-MM-DD HH:MM:SS）                       |
| `page`         | int    | 1      | 当前页码                                                      |
| `page_size`    | int    | 10     | 每页显示的用户条数                                                 |

- **返回**: 所有用户的简要信息

```json
{
    "users": [
        {
            "id": 1,
            "username": "username1",
            "email": "user1@example.com",
            "role": "publisher",
            "permission": 1,
            "date_joined": "2023-01-01 12:34:56"
        },
        {
            "id": 2,
            "username": "username2",
            "email": "user2@example.com",
            "role": "reviewer",
            "permission": 0,
            "date_joined": "2023-02-01 13:45:07"
        }
    ],
    "current_page": 1,
    "total_pages": 5,
    "total_users": 50,
    "has_next": true,
    "has_previous": false
}
```

#### 9. 创建新用户
- **URL**: `/create_user/`
- **方法**: `POST`
- **权限**: 需要管理员权限
- **参数**:
  - `username`: 用户名
  - `email`: 邮箱
  - `password`: 密码
  - `role`: 角色
- **返回**:
  - 成功创建用户的消息

```markdown
{
  "message": "User created successfully",
  "user_id": "用户ID"
}
```


#### 10. 更新用户信息
- **URL**: `/update_user/<int:user_id>/`
- **方法**: `PUT`
- **权限**: 需要管理员权限
- **参数**:
  - `username`: 用户名（可选）
  - `email`: 邮箱（可选）
  - `role`: 角色（可选）
  - `state`: 状态（可选）
  - `password`: 新密码（可选）
  - `permission`: 权限（可选）
- **返回**:
  - 成功更新用户的消息

```markdown
{
  "message": "User updated successfully"
}
```


#### 11. 删除用户
- **URL**: `/delete_user/<int:user_id>/`
- **方法**: `DELETE`
- **权限**: 需要管理员权限
- **返回**:
  - 成功删除用户的消息

```json
{
  "message": "User deleted successfully"
}
```

#### 12. 创建管理员
- **URL**: `/admin/create/`
- **方法**: `POST`
- **权限**: 需要超级管理员权限（`is_superuser` 为 `True`）
- **参数**:

| 参数名 | 类型   | 描述                             |
|--------|--------|----------------------------------|
| `username` | string | 用户名，必填                     |
| `email` | string | 用户邮箱，必填                     |
| `password` | string | 用户密码，必填                   |
| `role` | string | 角色，默认为 `admin`，可选         |

- **返回**: 创建成功返回包含 `message` 和 `user_id` 的信息。

```json
{
    "message": "Admin user created successfully",
    "user_id": "integer"
}
```

#### 13. 管理员登录
- **URL**: `/admin/login/`
- **方法**: `GET`
- **权限**: 需要管理员权限
- **参数**:

| 参数名 | 类型   | 描述                             |
|--------|--------|----------------------------------|
| `email` | string | 用户邮箱                         |
| `password` | string | 用户密码                       |
| `role` | string | 角色，必须为 `admin`             |

- **返回**: 登录成功返回包含 `access`、`refresh`、`role`、`profile` 和 `avatar` 的管理员相关信息。

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "role": "admin",
    "profile": "管理员简介",
    "avatar": "http://example.com/media/avatars/admin.png"
}
```
#### 14. 为Publisher关联Reviewer
**URL**: `/api/publisher-reviewer-associations/`
**方法**: `POST`
**权限**: 需要Publisher本人或管理员权限
**请求头**:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体参数**:

| 参数           | 类型    | 必填 | 约束                | 说明             |
| -------------- | ------- | ---- | ------------------- | ---------------- |
| `publisher_id` | int     | 是   | 必须为Publisher角色 | 发起关联的用户ID |
| `reviewer_id`  | int     | 是   | 必须为Reviewer角色  | 被关联的审核员ID |
| `is_active`    | boolean | 否   | 默认true            | 是否激活关联     |

**请求示例**:

```json
{
    "publisher_id": 123,
    "reviewer_id": 456,
    "is_active": true
}
```

**成功响应 (201 Created)**:

```json
{
    "status": "created",
    "relationship_id": 10,
    "publisher": "publisher1",
    "reviewer": "reviewer1",
    "is_active": true
}
```

---

## **8. 组织管理接口**

------

### **8.1 提交组织申请**

- **URL**: `/api/organizations/applications/`
- **方法**: `POST`
- **请求体**:

```
{
  "name": "string",               // 组织名称，必填
  "email": "string",              // 组织联系邮箱，必填
  "admin_username": "string",     // 管理员用户名，必填
  "admin_email": "string",        // 管理员邮箱，必填
  "admin_password": "string",     // 管理员密码，必填
  "proof_materials": "file",       // 组织证明材料文件（可选）
  "logo": "file",                 // 组织logo文件（可选）
  "description": "string"         // 组织描述（可选）
}
```

- **响应**:

  - **成功**:

    ```
    {
      "message": "Organization application submitted for review",
      "application_id": "integer"
    }
    ```

    - **状态码**: `201 Created`

  - **失败**（缺少必填字段）:

    ```
    {
      "message": "All required fields must be provided"
    }
    ```

    - **状态码**: `400 Bad Request`

------

### **8.2 获取待审核组织申请列表**

- **URL**: `/api/organizations/applications/pending/`

- **方法**: `GET`

- **查询参数**:

  - `query`: 搜索关键词（组织名或管理员邮箱）
  - `startTime`: 起始时间（ISO格式）
  - `endTime`: 结束时间（ISO格式）
  - `page`: 页码（默认1）
  - `page_size`: 每页数量（默认10）

- **响应**:

  ```
  {
    "applications": [
      {
        "id": "integer",
        "name": "string",
        "email": "string",
        "admin_username": "string",
        "admin_email": "string",
        "submitted_at": "string"
      }
    ],
    "current_page": "integer",
    "total_pages": "integer",
    "total_count": "integer",
    "has_next": "boolean",
    "has_previous": "boolean"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.3 获取待审核申请详情**

- **URL**: `/api/organizations/applications/pending/{app_id}/`

- **方法**: `GET`

- 

  响应

  :

  ```
  {
    "id": "integer",
    "name": "string",
    "email": "string",
    "admin_username": "string",
    "admin_email": "string",
    "description": "string",
    "logo": "string|null",
    "submitted_at": "string",
    "proof_materials": "string|null"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.4 批准组织申请**

- **URL**: `/api/organizations/applications/{app_id}/approve/`

- **方法**: `POST`

- 

  响应

  :

  - **成功**:

    ```
    {
      "message": "Organization approved successfully",
      "organization_id": "integer"
    }
    ```

    - **状态码**: `200 OK`

  - **失败**（申请不存在或已处理）:

    ```
    {
      "error": "Application not found or already processed"
    }
    ```

    - **状态码**: `404 Not Found`

------

### **8.5 拒绝组织申请**

- **URL**: `/api/organizations/applications/{app_id}/reject/`

- **方法**: `POST`

- 

  响应

  :

  ```
  {
    "message": "Organization application rejected"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.6 创建组织（管理员）**

- **URL**: `/api/organizations/root/`
- **方法**: `POST`
- **请求体**:

```
{
  "admin_email": "string",
  "admin_username": "string",
  "admin_password": "string",
  "org_name": "string",
  "email": "string",
  "description": "string",
  "logo": "file",
  "proof_materials": "file"
}
```

- 

  响应

  :

  ```
  {
    "message": "Organization created successfully",
    "organization_id": "integer"
  }
  ```

  - **状态码**: `201 Created`

------

### **8.7 获取组织列表**

- **URL**: `/api/organizations/`

- **方法**: `GET`

- **查询参数**:

  - `query`: 搜索关键词
  - `page`: 页码（默认1）
  - `page_size`: 每页数量（默认10）

- **响应**:

  ```
  {
    "organizations": [
      {
        "id": "integer",
        "name": "string",
        "description": "string",
        "logo": "string|null",
        "user_count": "integer",
        "image_count": "integer"
      }
    ],
    "current_page": "integer",
    "total_pages": "integer",
    "total_organizations": "integer",
    "has_next": "boolean",
    "has_previous": "boolean"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.8 获取组织详情**

- **URL**: `/api/organizations/{org_id}/`

- **方法**: `GET`

- 

  响应

  :

  ```
  {
    "id": "integer",
    "name": "string",
    "email": "string",
    "created_at": "string",
    "description": "string",
    "logo": "string|null",
    "proof_materials": "string|null",
    "user_count": "integer",
    "image_count": "integer"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.9 删除组织**

- **URL**: `/api/organizations/{org_id}/`

- **方法**: `DELETE`

- 

  响应

  :

  ```
  {
    "message": "Organization deleted successfully"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.10 更新组织角色权限**

- **URL**: `/api/organizations/{org_id}/permissions/`
- **方法**: `POST`
- **请求体**:

```
{
  "role": "string",       // "publisher" 或 "reviewer"
  "permission": "integer" // 权限值
}
```

- 

  响应

  :

  ```
  {
    "message": "{role} permissions updated successfully"
  }
  ```

  - **状态码**: `200 OK`

------

### **8.11 获取邀请码**

- **URL**: `/api/organizations/{org_id}/invitation-codes/`

- **方法**: `GET`

- 

  响应

  :

  ```
  [
    {
      "code": "string",
      "role": "string",
      "expires_at": "string"
    }
  ]
  ```

  - **状态码**: `200 OK`

------

```
# 通知系统 API 文档

## 获取用户通知列表
**URL**: `/api/notifications/`  
**方法**: GET  
**权限**: 需要认证  
**描述**: 获取当前用户的所有通知  
**响应**:  
成功返回格式:
```json
{
    "notifications": [
        {
            "id": 1,
            "sender_id": 2,
            "sender_name": "admin",
            "category": "全局通知",
            "title": "系统维护",
            "content": "系统将于今晚进行维护",
            "status": "unread",
            "notified_at": "2023-01-01 12:00:00",
            "url": "/maintenance"
        }
    ]
}
```

失败返回格式:

```
{"error": "错误信息"}
```

## 9. 通知接口

### 9.1 获取未读通知数量

**URL**: `/api/notifications/status/`
 ​**​方法​**: GET
 ​**​权限​**: 需要认证
 ​**​描述​**: 获取当前用户的未读通知数量
 ​**​响应​**:
 成功返回格式:

```
{"not_read": 5}
```

失败返回格式:

```
{"error": "错误信息"}
```

### 9.2 标记所有通知为已读

**URL**: `/api/notifications/mark-all-read/`
 ​**​方法​**: POST
 ​**​权限​**: 需要认证
 ​**​描述​**: 将当前用户的所有未读通知标记为已读
 ​**​响应​**:
 成功返回格式:

```
{"message": "All notifications marked as read"}
```

失败返回格式:

```
{"error": "错误信息"}
```

### 9.3 标记单个通知为已读

**URL**: `/api/notifications/mark-read/{notification_id}/`
 ​**​方法​**: POST
 ​**​权限​**: 需要认证
 ​**​参数​**:

- `notification_id`: 要标记的通知ID
   ​**​描述​**: 将指定ID的通知标记为已读
   ​**​响应​**:
   成功返回格式:

```
{"message": "Notification marked as read"}
```

失败返回格式:

```
{"error": "错误信息"}
```

### 9.4 发送全局公告

**URL**: `/api/notifications/broadcast/`
 ​**​方法​**: POST
 ​**​权限​**: 需要管理员权限
 ​**​请求参数​**:

```
{
    "title": "公告标题",
    "content": "公告内容"
}
```

**参数限制**:

- 标题: 必填，最大15个字符
- 内容: 必填，最大1000个字符

**描述**: 向所有非管理员用户发送全局公告
 ​**​响应​**:
 成功返回格式:

```
{"message": "公告发送成功"}
```

失败返回格式:

```
{"error": "错误信息"}
undefined
```