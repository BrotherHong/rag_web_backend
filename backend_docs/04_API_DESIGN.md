# 🔌 API 端點設計

> **重要**: 所有 API 端點必須與前端 `src/services/api/` 模組完全對應

## API 基礎路徑

```
開發環境: http://localhost:8000/api
生產環境: https://your-domain.com/api
```

---

## 1. 認證模組 (Auth)

### POST /api/auth/login
使用者登入

**前端對應**: `api/auth.js` → `login()`

```javascript
// 請求
{
  "username": "admin",
  "password": "admin123"
}

// 回應
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@ncku.edu.tw",
    "fullName": "系統管理員",
    "role": "super_admin",
    "isSuperAdmin": true,
    "department": {
      "id": 1,
      "name": "人事室",
      "code": "HR"
    }
  }
}
```

**FastAPI 實作**:
```python
@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    # 1. 驗證使用者
    user = await user_service.authenticate(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    # 2. 生成 JWT Token
    token = create_access_token(data={"sub": user.username, "user_id": user.id})
    
    # 3. 儲存 Session (Redis)
    await redis.setex(f"session:{user.id}", 86400, token)
    
    # 4. 記錄登入活動
    await activity_service.log_activity(
        db, user_id=user.id, action="login", 
        description=f"{user.username} 登入系統"
    )
    
    # 5. 更新最後登入時間
    await user_service.update_last_login(db, user.id)
    
    return LoginResponse(token=token, user=UserSchema.from_orm(user))
```

---

### POST /api/auth/logout
使用者登出

**前端對應**: `api/auth.js` → `logout()`

```javascript
// 請求 (需 Authorization Header)
Headers: { Authorization: "Bearer <token>" }

// 回應
{ "message": "登出成功" }
```

**FastAPI 實作**:
```python
@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    # 1. 刪除 Redis Session
    await redis.delete(f"session:{current_user.id}")
    
    # 2. 記錄登出活動
    await activity_service.log_activity(
        db, user_id=current_user.id, action="logout",
        description=f"{current_user.username} 登出系統"
    )
    
    return {"message": "登出成功"}
```

---

### GET /api/auth/verify
驗證 Token

**前端對應**: `api/auth.js` → `verifyToken()`

```javascript
// 請求
Headers: { Authorization: "Bearer <token>" }

// 回應
{
  "valid": true,
  "user": { /* 使用者資訊 */ }
}
```

---

## 2. 檔案管理模組 (Files)

### GET /api/files
取得檔案列表

**前端對應**: `api/files.js` → `getFiles()`

```javascript
// 請求 (查詢參數)
?page=1&limit=10&category_id=1&search=規章&sort=created_at&order=desc

// 回應
{
  "items": [
    {
      "id": 1,
      "filename": "personnel_rules_v1.pdf",
      "originalFilename": "人事規章.pdf",
      "fileSize": 2048576,
      "fileType": "pdf",
      "category": {
        "id": 1,
        "name": "人事規章",
        "color": "blue"
      },
      "uploader": {
        "id": 2,
        "username": "hr_admin",
        "fullName": "人事管理員"
      },
      "status": "completed",
      "isVectorized": true,
      "vectorCount": 45,
      "downloadCount": 12,
      "createdAt": "2025-10-15T10:30:00Z",
      "updatedAt": "2025-10-15T10:35:00Z"
    }
  ],
  "total": 156,
  "page": 1,
  "pages": 16
}
```

**FastAPI 實作**:
```python
@router.get("/", response_model=FileListResponse)
async def get_files(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    sort: str = Query("created_at", regex="^(filename|created_at|file_size)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. 建立基礎查詢 (自動過濾處室)
    query = select(File).where(File.department_id == current_user.department_id)
    
    # 2. 分類篩選
    if category_id:
        query = query.where(File.category_id == category_id)
    
    # 3. 搜尋
    if search:
        query = query.where(
            or_(
                File.original_filename.ilike(f"%{search}%"),
                File.description.ilike(f"%{search}%")
            )
        )
    
    # 4. 排序
    order_by = desc(getattr(File, sort)) if order == "desc" else asc(getattr(File, sort))
    query = query.order_by(order_by)
    
    # 5. 分頁
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # 6. 執行查詢
    result = await db.execute(query)
    files = result.scalars().all()
    
    return FileListResponse(
        items=[FileSchema.from_orm(f) for f in files],
        total=total,
        page=page,
        pages=math.ceil(total / limit)
    )
```

---

### POST /api/files/upload
上傳檔案

**前端對應**: `api/files.js` → `uploadFile()`

```javascript
// 請求 (multipart/form-data)
FormData {
  file: File,
  category_id: 1,
  description: "2025年人事規章"
}

// 回應
{
  "id": 123,
  "filename": "20251031_123456_personnel_rules.pdf",
  "originalFilename": "人事規章.pdf",
  "fileSize": 2048576,
  "status": "pending",
  "message": "檔案上傳成功，正在處理中..."
}
```

**FastAPI 實作**:
```python
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category_id: int = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    # 1. 驗證檔案
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案過大")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支援的檔案格式")
    
    # 2. 生成唯一檔名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
    
    # 3. 儲存實體檔案
    file_path = os.path.join(settings.UPLOAD_DIR, str(current_user.department_id), unique_filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # 4. 建立資料庫記錄
    db_file = File(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file.size,
        file_type=ext[1:],
        mime_type=file.content_type,
        category_id=category_id,
        department_id=current_user.department_id,
        uploader_id=current_user.id,
        description=description,
        status="pending"
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    
    # 5. 觸發背景處理任務 (Celery)
    process_file_task.delay(db_file.id)
    
    # 6. 記錄活動
    await activity_service.log_activity(
        db, user_id=current_user.id, action="upload",
        entity_type="file", entity_id=db_file.id,
        description=f"上傳檔案: {file.filename}"
    )
    
    return FileUploadResponse.from_orm(db_file)
```

---

### GET /api/files/{file_id}
取得檔案詳情

**前端對應**: `api/files.js` → `getFile()` （注意：前端未實作此功能）

```javascript
// 回應
{
  "id": 1,
  "filename": "personnel_rules_v1.pdf",
  "originalFilename": "人事規章.pdf",
  "fileSize": 2048576,
  "fileType": "pdf",
  "mimeType": "application/pdf",
  "category": {
    "id": 1,
    "name": "人事規章",
    "color": "blue"
  },
  "uploader": {
    "id": 2,
    "username": "hr_admin",
    "fullName": "人事管理員"
  },
  "department": {
    "id": 1,
    "name": "人事室"
  },
  "status": "completed",
  "isVectorized": true,
  "vectorCount": 45,
  "downloadCount": 12,
  "description": "2025年人事規章",
  "createdAt": "2025-10-15T10:30:00Z",
  "updatedAt": "2025-10-15T10:35:00Z",
  "lastAccessed": "2025-11-12T09:00:00Z"
}
```

**FastAPI 實作**:
```python
@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得檔案詳細資訊
    
    - 包含完整的檔案元資料
    - 權限檢查：只能查看自己處室的檔案
    """
    query = await db.execute(
        select(File)
        .where(File.id == file_id)
        .options(
            joinedload(File.category),
            joinedload(File.uploader),
            joinedload(File.department)
        )
    )
    file = query.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 權限檢查
    if file.department_id != current_user.department_id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限查看此檔案")
    
    return FileDetailResponse.from_orm(file)
```

---

### PUT /api/files/{file_id}
更新檔案資訊

**前端對應**: `api/files.js` → `updateFile()` （注意：前端未實作此功能）

```javascript
// 請求
{
  "categoryId": 2,
  "description": "更新後的描述"
}

// 回應
{
  "message": "檔案資訊已更新"
}
```

**FastAPI 實作**:
```python
@router.put("/{file_id}")
async def update_file(
    file_id: int,
    file_data: FileUpdate,
    current_user: User = Depends(get_current_active_admin),  # 需要管理員權限
    db: AsyncSession = Depends(get_db)
):
    """
    更新檔案資訊
    
    - 可更新分類、描述等元資料
    - 不能更新檔案實體內容
    """
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 權限檢查
    if file.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="無權限修改此檔案")
    
    # 更新分類
    if file_data.category_id:
        # 驗證分類是否存在且屬於同一處室
        category = await db.get(Category, file_data.category_id)
        if not category or category.department_id != current_user.department_id:
            raise HTTPException(status_code=400, detail="分類不存在或無權使用")
        file.category_id = file_data.category_id
    
    # 更新描述
    if file_data.description is not None:
        file.description = file_data.description
    
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="file",
        entity_id=file_id,
        description=f"更新檔案資訊: {file.original_filename}"
    )
    
    return {"message": "檔案資訊已更新"}
```

**Schema 定義**:
```python
# app/schemas/file.py (新增)
class FileUpdate(BaseModel):
    """更新檔案資訊"""
    category_id: Optional[int] = None
    description: Optional[str] = None

class FileDetailResponse(BaseModel):
    """檔案詳細資訊"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    mime_type: str
    category: CategorySchema
    uploader: UserSchema
    department: DepartmentSchema
    status: str
    is_vectorized: bool
    vector_count: Optional[int]
    download_count: int
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    
    class Config:
        from_attributes = True
```

---

### DELETE /api/files/{file_id}
刪除檔案

**前端對應**: `api/files.js` → `deleteFile()`

```python
@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. 取得檔案
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 2. 權限檢查
    if file.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="無權限刪除此檔案")
    
    # 3. 刪除實體檔案
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # 4. 刪除 Qdrant 向量
    if file.is_vectorized:
        await qdrant_service.delete_vectors(file_id)
    
    # 5. 刪除資料庫記錄
    await db.delete(file)
    await db.commit()
    
    # 6. 記錄活動
    await activity_service.log_activity(
        db, user_id=current_user.id, action="delete",
        entity_type="file", entity_id=file_id,
        description=f"刪除檔案: {file.original_filename}"
    )
    
    return {"message": "檔案已刪除"}
```

---

### GET /api/files/{file_id}/download
下載檔案

**前端對應**: `api/files.js` → `downloadFile()`

```python
@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. 取得檔案
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    # 2. 權限檢查
    if file.department_id != current_user.department_id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限下載此檔案")
    
    # 3. 更新下載次數
    file.download_count += 1
    file.last_accessed = datetime.now()
    await db.commit()
    
    # 4. 記錄活動
    await activity_service.log_activity(
        db, user_id=current_user.id, action="download",
        entity_type="file", entity_id=file_id,
        description=f"下載檔案: {file.original_filename}"
    )
    
    # 5. 返回檔案
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type=file.mime_type
    )
```

---

## 3. 分類管理模組 (Categories)

### GET /api/categories
取得分類列表

**前端對應**: `api/categories.js` → `getCategories()` 和 `getCategoriesWithDetails()`

```javascript
// 回應（完整資訊）
{
  "items": [
    {
      "id": 1,
      "name": "人事規章",
      "color": "blue",
      "fileCount": 23,
      "createdAt": "2025-01-01T00:00:00Z"
    }
  ]
}

// 前端會自動將「未分類」排在最後
```

**FastAPI 實作**:
```python
@router.get("/", response_model=CategoryListResponse)
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得分類列表（自動過濾處室）"""
    query = select(Category).where(
        Category.department_id == current_user.department_id
    ).order_by(Category.name)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return CategoryListResponse(items=categories)
```

---

### POST /api/categories
新增分類

**前端對應**: `api/categories.js` → `addCategory()`

```javascript
// 請求
{
  "name": "新分類",
  "color": "blue"
}

// 回應
{
  "id": 10,
  "name": "新分類",
  "color": "blue",
  "fileCount": 0,
  "createdAt": "2025-11-06T10:00:00Z"
}
```

**FastAPI 實作**:
```python
@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),  # 需要管理員權限
    db: AsyncSession = Depends(get_db)
):
    """新增分類"""
    # 檢查分類名稱是否重複
    existing = await db.execute(
        select(Category).where(
            Category.name == category_data.name,
            Category.department_id == current_user.department_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分類名稱已存在")
    
    # 建立分類
    category = Category(
        name=category_data.name,
        color=category_data.color,
        department_id=current_user.department_id
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category
```

---

### DELETE /api/categories/{category_id}
刪除分類

**前端對應**: `api/categories.js` → `deleteCategory()`

```javascript
// 回應
{
  "message": "分類已刪除"
}
```

**FastAPI 實作**:
```python
@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_admin),  # 需要管理員權限
    db: AsyncSession = Depends(get_db)
):
    """刪除分類"""
    category = await db.get(Category, category_id)
    
    if not category:
        raise HTTPException(status_code=404, detail="分類不存在")
    
    # 權限檢查
    if category.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="無權限刪除此分類")
    
    # 檢查是否有檔案使用此分類
    file_count = await db.scalar(
        select(func.count(File.id)).where(File.category_id == category_id)
    )
    
    if file_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此分類下還有 {file_count} 個檔案，無法刪除"
        )
    
    await db.delete(category)
    await db.commit()
    
    return {"message": "分類已刪除"}
```

---

### GET /api/categories/stats
分類統計

**前端對應**: `api/categories.js` → `getCategoryStats()`（已定義但前端組件未實際使用）

```javascript
// 回應
{
  "stats": [
    {
      "id": 1,
      "name": "人事規章",
      "color": "blue",
      "fileCount": 23,
      "totalSize": 52428800,
      "percentage": 35.5
    }
  ]
}
```

**FastAPI 實作**:
```python
@router.get("/stats", response_model=CategoryStatsResponse)
async def get_category_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得分類統計資料
    
    - 各分類的檔案數量
    - 各分類的總大小
    - 佔比百分比
    """
    # 查詢各分類的統計
    query = await db.execute(
        select(
            Category.id,
            Category.name,
            Category.color,
            func.count(File.id).label('file_count'),
            func.coalesce(func.sum(File.file_size), 0).label('total_size')
        )
        .outerjoin(File, File.category_id == Category.id)
        .where(Category.department_id == current_user.department_id)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(desc('file_count'))
    )
    
    results = query.all()
    
    # 計算總大小（用於計算百分比）
    total_size = sum(row.total_size for row in results)
    
    # 組織結果
    stats = []
    for row in results:
        percentage = (row.total_size / total_size * 100) if total_size > 0 else 0
        stats.append({
            "id": row.id,
            "name": row.name,
            "color": row.color,
            "file_count": row.file_count,
            "total_size": row.total_size,
            "percentage": round(percentage, 1)
        })
    
    return CategoryStatsResponse(stats=stats)
```

**Schema 定義**:
```python
# app/schemas/category.py (新增)
class CategoryStatItem(BaseModel):
    """分類統計項目"""
    id: int
    name: str
    color: str
    file_count: int
    total_size: int
    percentage: float

class CategoryStatsResponse(BaseModel):
    """分類統計回應"""
    stats: List[CategoryStatItem]
```

**注意**: 此端點在前端 API 模組中有定義，但目前前端組件中並未實際調用此功能。保留實作以供未來統計儀表板使用。

---

## 4. 活動記錄模組 (Activities)

### GET /api/activities
取得活動記錄

**前端對應**: `api/activities.js` → `getActivities()` 和 `getRecentActivities()`

```javascript
// 請求
?page=1&limit=20&action=upload&start_date=2025-10-01

// 回應
{
  "items": [
    {
      "id": 1001,
      "username": "hr_admin",
      "action": "upload",
      "description": "上傳檔案: 人事規章.pdf",
      "entityType": "file",
      "entityId": 123,
      "ipAddress": "192.168.1.100",
      "createdAt": "2025-10-31T14:30:00Z"
    }
  ],
  "total": 5432,
  "page": 1,
  "pages": 272
}
```

---

### GET /api/activities/all
取得所有處室的活動記錄（僅供超級管理員）

**前端對應**: `api/activities.js` → `getAllActivities()`

```javascript
// 請求
?departmentId=1&limit=50

// 回應
{
  "items": [
    {
      "id": 1001,
      "username": "hr_admin",
      "departmentName": "人事室",
      "action": "upload",
      "description": "上傳檔案: 人事規章.pdf",
      "createdAt": "2025-10-31T14:30:00Z"
    }
  ],
  "total": 5432
}
```

**FastAPI 實作**:
```python
@router.get("/all", response_model=ActivityListResponse)
async def get_all_activities(
    department_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_super_admin),  # 僅超級管理員
    db: AsyncSession = Depends(get_db)
):
    """取得所有處室的活動記錄"""
    query = select(Activity).options(
        joinedload(Activity.user),
        joinedload(Activity.department)
    )
    
    # 可選的處室過濾
    if department_id:
        query = query.where(Activity.department_id == department_id)
    
    query = query.order_by(desc(Activity.created_at)).limit(limit)
    
    result = await db.execute(query)
    activities = result.scalars().unique().all()
    
    return ActivityListResponse(
        items=activities,
        total=len(activities)
    )
```

---

### GET /api/statistics
取得系統統計資料

**前端對應**: `api/activities.js` → `getStatistics()`

```javascript
// 回應
{
  "totalFiles": 234,
  "filesByCategory": {
    "人事規章": 45,
    "請假相關": 32,
    "薪資福利": 28
  },
  "monthlyQueries": [120, 145, 167, 189, 203],
  "systemStatus": "healthy",
  "storageUsed": "2.5 GB",
  "storageTotal": "10 GB"
}
```

**FastAPI 實作**:
```python
@router.get("/", response_model=StatisticsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得統計資料（自動過濾處室）"""
    # 總檔案數
    total_files = await db.scalar(
        select(func.count(File.id))
        .where(File.department_id == current_user.department_id)
    )
    
    # 各分類檔案數
    files_by_category = await db.execute(
        select(Category.name, func.count(File.id))
        .join(File, File.category_id == Category.id)
        .where(Category.department_id == current_user.department_id)
        .group_by(Category.name)
    )
    category_stats = {name: count for name, count in files_by_category}
    
    # 儲存空間使用
    storage_used = await db.scalar(
        select(func.sum(File.file_size))
        .where(File.department_id == current_user.department_id)
    ) or 0
    
    return StatisticsResponse(
        total_files=total_files,
        files_by_category=category_stats,
        monthly_queries=[],  # 可從其他表查詢
        system_status="healthy",
        storage_used=f"{storage_used / (1024**3):.2f} GB",
        storage_total="10 GB"  # 從設定讀取
    )
```

---

## 5. 批次上傳模組 (Upload)

### POST /api/files/check-duplicates
檢查重複檔案

**前端對應**: `api/upload.js` → `checkDuplicates()`

```javascript
// 請求
{
  "files": [
    { "name": "人事規章.pdf", "size": 2048576, "type": "application/pdf" },
    { "name": "薪資表.xlsx", "size": 1024000, "type": "application/vnd.ms-excel" }
  ]
}

// 回應
{
  "results": [
    {
      "fileName": "人事規章.pdf",
      "isDuplicate": true,
      "duplicateFile": {
        "id": 123,
        "originalFilename": "人事規章.pdf",
        "uploadDate": "2024-10-15",
        "uploader": "張三"
      },
      "relatedFiles": [
        {
          "id": 124,
          "originalFilename": "人事規章_v2.pdf",
          "uploadDate": "2024-10-20"
        }
      ],
      "suggestReplace": true
    },
    {
      "fileName": "薪資表.xlsx",
      "isDuplicate": false,
      "duplicateFile": null,
      "relatedFiles": [],
      "suggestReplace": false
    }
  ]
}
```

**FastAPI 實作**:
```python
@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(
    request: DuplicateCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    檢查檔案是否重複並找出相關檔案
    
    - 根據檔案名稱和大小判斷是否為重複檔案
    - 搜尋相似檔名的相關檔案
    - 建議是否應該替換舊檔案
    """
    results = []
    
    for file_info in request.files:
        # 1. 檢查完全相同的檔案（檔名 + 大小）
        duplicate_query = await db.execute(
            select(File).where(
                File.original_filename == file_info.name,
                File.file_size == file_info.size,
                File.department_id == current_user.department_id
            ).options(joinedload(File.uploader))
        )
        duplicate_file = duplicate_query.scalar_one_or_none()
        
        # 2. 搜尋相關檔案（相似檔名）
        base_name = os.path.splitext(file_info.name)[0]
        related_query = await db.execute(
            select(File).where(
                File.original_filename.ilike(f"%{base_name}%"),
                File.department_id == current_user.department_id
            ).limit(5)
        )
        related_files = related_query.scalars().all()
        
        # 3. 建構結果
        result = DuplicateCheckResult(
            file_name=file_info.name,
            is_duplicate=duplicate_file is not None,
            duplicate_file=DuplicateFileInfo.from_orm(duplicate_file) if duplicate_file else None,
            related_files=[RelatedFileInfo.from_orm(f) for f in related_files if f.id != (duplicate_file.id if duplicate_file else None)],
            suggest_replace=duplicate_file is not None
        )
        results.append(result)
    
    return DuplicateCheckResponse(results=results)
```

**Schema 定義**:
```python
# app/schemas/upload.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileInfoInput(BaseModel):
    """檔案資訊輸入"""
    name: str
    size: int
    type: str

class DuplicateCheckRequest(BaseModel):
    """重複檢查請求"""
    files: List[FileInfoInput]

class DuplicateFileInfo(BaseModel):
    """重複檔案資訊"""
    id: int
    original_filename: str
    upload_date: str
    uploader: str
    
    class Config:
        from_attributes = True

class RelatedFileInfo(BaseModel):
    """相關檔案資訊"""
    id: int
    original_filename: str
    upload_date: str
    
    class Config:
        from_attributes = True

class DuplicateCheckResult(BaseModel):
    """單一檔案的重複檢查結果"""
    file_name: str
    is_duplicate: bool
    duplicate_file: Optional[DuplicateFileInfo]
    related_files: List[RelatedFileInfo]
    suggest_replace: bool

class DuplicateCheckResponse(BaseModel):
    """重複檢查回應"""
    results: List[DuplicateCheckResult]
```

---

### POST /api/upload/batch
批次上傳檔案

**前端對應**: `api/upload.js` → `batchUpload()`

```javascript
// 請求 (multipart/form-data)
FormData {
  files: [File, File, File],
  categories: {"file1.pdf": 1, "file2.docx": 2},
  removeFileIds: [123, 124]  // 要替換/刪除的舊檔案 ID
}

// 回應
{
  "taskId": "task_20241112_143000_abc123",
  "message": "上傳任務已建立，開始處理檔案"
}
```

**FastAPI 實作**:
```python
@router.post("/batch", response_model=BatchUploadResponse)
async def batch_upload(
    files: List[UploadFile] = File(...),
    categories: str = Form(...),  # JSON string
    remove_file_ids: str = Form(default="[]"),  # JSON string
    current_user: User = Depends(get_current_active_admin),  # 需要管理員權限
    db: AsyncSession = Depends(get_db)
):
    """
    批次上傳檔案並建立處理任務
    
    - 支援為每個檔案指定不同的分類
    - 支援替換/刪除舊檔案
    - 使用 Celery 背景任務處理
    """
    import json
    
    # 解析參數
    categories_dict = json.loads(categories)
    remove_ids = json.loads(remove_file_ids)
    
    # 1. 生成任務 ID
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    # 2. 建立上傳任務記錄
    upload_task = UploadTask(
        task_id=task_id,
        user_id=current_user.id,
        department_id=current_user.department_id,
        total_files=len(files),
        status="pending"
    )
    db.add(upload_task)
    await db.commit()
    
    # 3. 刪除要替換的舊檔案
    if remove_ids:
        await db.execute(
            delete(File).where(
                File.id.in_(remove_ids),
                File.department_id == current_user.department_id
            )
        )
        await db.commit()
    
    # 4. 觸發 Celery 批次處理任務
    batch_upload_task.delay(
        task_id=task_id,
        files_data=[{
            "filename": f.filename,
            "content_type": f.content_type,
            "category_id": categories_dict.get(f.filename)
        } for f in files],
        user_id=current_user.id,
        department_id=current_user.department_id
    )
    
    return BatchUploadResponse(
        task_id=task_id,
        message="上傳任務已建立，開始處理檔案"
    )
```

**資料庫模型**:
```python
# app/models/upload_task.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base, TimestampMixin

class UploadTask(Base, TimestampMixin):
    """批次上傳任務記錄"""
    __tablename__ = 'upload_tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, default=0)
    successful_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    error_message = Column(Text)
    result_data = Column(JSONB)  # 詳細結果資訊
```

---

### GET /api/upload/progress/{task_id}
查詢上傳任務進度

**前端對應**: `api/upload.js` → `getUploadProgress()`

```javascript
// 回應（完整任務資訊）
{
  "id": 1,
  "taskId": "task_20241112_143000_abc123",
  "userId": 2,
  "userName": "張三",
  "departmentId": 1,
  "departmentName": "人事室",
  "totalFiles": 10,
  "processedFiles": 7,
  "successfulFiles": 6,
  "failedFiles": 1,
  "status": "processing",
  "errorMessage": null,
  "resultData": {
    "files": [
      {
        "filename": "file1.pdf",
        "status": "success",
        "fileId": 456
      },
      {
        "filename": "file2.pdf",
        "status": "failed",
        "error": "檔案格式不支援"
      }
    ]
  },
  "createdAt": "2024-11-12T14:30:00Z",
  "updatedAt": "2024-11-12T14:35:00Z"
}
```

**FastAPI 實作**:
```python
@router.get("/progress/{task_id}", response_model=UploadTaskResponse)
async def get_upload_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查詢上傳任務進度
    
    - 返回任務的即時狀態
    - 包含每個檔案的處理結果
    """
    query = await db.execute(
        select(UploadTask)
        .where(UploadTask.task_id == task_id)
        .options(
            joinedload(UploadTask.user),
            joinedload(UploadTask.department)
        )
    )
    task = query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    # 權限檢查：只能查看自己的任務或超級管理員可查看所有
    if task.user_id != current_user.id and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="無權限查看此任務")
    
    return UploadTaskResponse.from_orm(task)
```

---

### GET /api/upload/tasks
取得使用者的上傳任務列表

**前端對應**: `api/upload.js` → `getUserUploadTasks()`

```javascript
// 回應
{
  "items": [
    {
      "id": 1,
      "taskId": "task_20241112_143000_abc123",
      "totalFiles": 10,
      "processedFiles": 10,
      "successfulFiles": 9,
      "failedFiles": 1,
      "status": "completed",
      "createdAt": "2024-11-12T14:30:00Z"
    },
    {
      "id": 2,
      "taskId": "task_20241112_100000_def456",
      "totalFiles": 5,
      "processedFiles": 3,
      "successfulFiles": 3,
      "failedFiles": 0,
      "status": "processing",
      "createdAt": "2024-11-12T10:00:00Z"
    }
  ]
}
```

**FastAPI 實作**:
```python
@router.get("/tasks", response_model=UploadTaskListResponse)
async def get_user_upload_tasks(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得使用者的上傳任務列表
    
    - 按建立時間倒序排列
    - 只返回當前使用者的任務
    """
    query = await db.execute(
        select(UploadTask)
        .where(UploadTask.user_id == current_user.id)
        .order_by(desc(UploadTask.created_at))
        .limit(limit)
    )
    tasks = query.scalars().all()
    
    return UploadTaskListResponse(items=tasks)
```

---

### DELETE /api/upload/tasks/{task_id}
刪除已完成的上傳任務記錄

**前端對應**: `api/upload.js` → `deleteUploadTask()`

```javascript
// 回應
{
  "message": "任務記錄已刪除"
}
```

**FastAPI 實作**:
```python
@router.delete("/tasks/{task_id}")
async def delete_upload_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除已完成的上傳任務記錄
    
    - 只能刪除已完成或失敗的任務
    - 只能刪除自己的任務
    """
    task = await db.scalar(
        select(UploadTask).where(UploadTask.task_id == task_id)
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    # 權限檢查
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="無權限刪除此任務")
    
    # 狀態檢查：只能刪除已完成或失敗的任務
    if task.status not in ['completed', 'failed']:
        raise HTTPException(status_code=400, detail="只能刪除已完成或失敗的任務")
    
    await db.delete(task)
    await db.commit()
    
    return {"message": "任務記錄已刪除"}
```

**Schema 定義**:
```python
# app/schemas/upload.py (續)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class BatchUploadResponse(BaseModel):
    """批次上傳回應"""
    task_id: str
    message: str

class UploadTaskResponse(BaseModel):
    """上傳任務詳細資訊"""
    id: int
    task_id: str
    user_id: int
    user_name: str
    department_id: int
    department_name: str
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    status: str
    error_message: Optional[str]
    result_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UploadTaskListResponse(BaseModel):
    """上傳任務列表回應"""
    items: List[UploadTaskResponse]
```

---

## 6. 使用者管理模組 (Users)

### GET /api/users
取得使用者列表（僅超級管理員）

**前端對應**: `api/users.js` → `getUsers()`

```javascript
// 回應
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "name": "系統管理員",
      "email": "admin@ncku.edu.tw",
      "role": "super_admin",
      "departmentId": null,
      "departmentName": null,
      "status": "active",
      "lastLogin": "2025-11-12T10:00:00Z",
      "createdAt": "2025-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "username": "hr_admin",
      "name": "人事管理員",
      "email": "hr@ncku.edu.tw",
      "role": "admin",
      "departmentId": 1,
      "departmentName": "人事室",
      "status": "active",
      "lastLogin": "2025-11-12T09:30:00Z",
      "createdAt": "2025-01-15T00:00:00Z"
    }
  ],
  "total": 25
}
```

**FastAPI 實作**:
```python
@router.get("/", response_model=UserListResponse)
async def get_users(
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_super_admin),  # 僅超級管理員
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有使用者列表
    
    - 支援按處室、狀態、角色篩選
    - 支援搜尋使用者名稱或帳號
    """
    query = select(User).options(joinedload(User.department))
    
    # 篩選條件
    if department_id:
        query = query.where(User.department_id == department_id)
    if status:
        query = query.where(User.status == status)
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().unique().all()
    
    return UserListResponse(
        items=[UserSchema.from_orm(u) for u in users],
        total=len(users)
    )
```

---

### POST /api/users
新增使用者

**前端對應**: `api/users.js` → `addUser()`

```javascript
// 請求
{
  "username": "new_user",
  "password": "password123",
  "name": "新使用者",
  "email": "new_user@ncku.edu.tw",
  "role": "user",
  "departmentId": 1
}

// 回應
{
  "id": 26,
  "username": "new_user",
  "name": "新使用者",
  "email": "new_user@ncku.edu.tw",
  "role": "user",
  "departmentId": 1,
  "status": "active"
}
```

**FastAPI 實作**:
```python
@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    新增使用者
    
    - 檢查使用者名稱和 Email 是否重複
    - 密碼自動加密
    - 驗證處室是否存在
    """
    # 檢查使用者名稱是否重複
    existing_username = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="使用者名稱已存在")
    
    # 檢查 Email 是否重複
    if user_data.email:
        existing_email = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email 已被使用")
    
    # 驗證處室是否存在
    if user_data.department_id:
        department = await db.get(Department, user_data.department_id)
        if not department:
            raise HTTPException(status_code=404, detail="處室不存在")
    
    # 建立使用者
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        full_name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        department_id=user_data.department_id,
        status="active",
        is_super_admin=(user_data.role == "super_admin")
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="user",
        entity_id=new_user.id,
        description=f"建立使用者: {new_user.username}"
    )
    
    return UserResponse.from_orm(new_user)
```

---

### PUT /api/users/{user_id}
更新使用者

**前端對應**: `api/users.js` → `updateUser()`

```javascript
// 請求
{
  "name": "更新後的名稱",
  "email": "updated@ncku.edu.tw",
  "role": "admin",
  "departmentId": 2,
  "status": "active"
}

// 回應
{
  "message": "使用者更新成功"
}
```

**FastAPI 實作**:
```python
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    更新使用者資訊
    
    - 可更新基本資訊、角色、處室
    - 不允許修改自己的角色和狀態
    - 檢查 Email 重複
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    # 不允許修改自己的角色和狀態
    if user_id == current_user.id:
        if user_data.role and user_data.role != user.role:
            raise HTTPException(status_code=400, detail="無法修改自己的角色")
        if user_data.status and user_data.status != user.status:
            raise HTTPException(status_code=400, detail="無法修改自己的狀態")
    
    # 檢查 Email 重複
    if user_data.email and user_data.email != user.email:
        existing_email = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != user_id
            )
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email 已被使用")
    
    # 驗證處室
    if user_data.department_id and user_data.department_id != user.department_id:
        department = await db.get(Department, user_data.department_id)
        if not department:
            raise HTTPException(status_code=404, detail="處室不存在")
    
    # 更新欄位
    if user_data.name:
        user.full_name = user_data.name
    if user_data.email:
        user.email = user_data.email
    if user_data.role:
        user.role = user_data.role
        user.is_super_admin = (user_data.role == "super_admin")
    if user_data.department_id is not None:
        user.department_id = user_data.department_id
    if user_data.status:
        user.status = user_data.status
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)
    
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="user",
        entity_id=user_id,
        description=f"更新使用者: {user.username}"
    )
    
    return {"message": "使用者更新成功"}
```

---

### DELETE /api/users/{user_id}
刪除使用者

**前端對應**: `api/users.js` → `deleteUser()`

```javascript
// 回應
{
  "message": "使用者刪除成功"
}
```

**FastAPI 實作**:
```python
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除使用者
    
    - 不允許刪除自己
    - 不允許刪除最後一個超級管理員
    - 檢查使用者是否有相關檔案
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    # 不允許刪除自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="無法刪除自己的帳號")
    
    # 檢查是否為最後一個超級管理員
    if user.is_super_admin:
        super_admin_count = await db.scalar(
            select(func.count(User.id)).where(User.is_super_admin == True)
        )
        if super_admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="無法刪除最後一個超級管理員"
            )
    
    # 檢查使用者是否有上傳檔案
    file_count = await db.scalar(
        select(func.count(File.id)).where(File.uploader_id == user_id)
    )
    if file_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此使用者有 {file_count} 個已上傳檔案，無法刪除。請先將檔案轉移或刪除。"
        )
    
    # 刪除使用者
    await db.delete(user)
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="delete",
        entity_type="user",
        entity_id=user_id,
        description=f"刪除使用者: {user.username}"
    )
    
    return {"message": "使用者刪除成功"}
```

**Schema 定義**:
```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """使用者基礎 Schema"""
    username: str
    name: str
    email: Optional[EmailStr] = None
    role: str
    department_id: Optional[int] = None

class UserCreate(UserBase):
    """建立使用者"""
    password: str

class UserUpdate(BaseModel):
    """更新使用者（所有欄位可選）"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    status: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    """使用者回應"""
    id: int
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """使用者列表回應"""
    items: List[UserResponse]
    total: int
```

---

## 7. 處室管理模組 (Departments)

### GET /api/departments
取得處室列表（僅超級管理員）

**前端對應**: `api/departments.js` → `getDepartments()`

```javascript
// 回應
{
  "items": [
    {
      "id": 1,
      "name": "人事室",
      "description": "負責人事相關業務",
      "color": "red",
      "userCount": 5,
      "fileCount": 234,
      "createdAt": "2025-01-01T00:00:00Z",
      "settings": {
        "maxFileSize": 52428800,
        "allowedExtensions": [".pdf", ".docx", ".txt"]
      }
    },
    {
      "id": 2,
      "name": "會計室",
      "description": "負責會計相關業務",
      "color": "blue",
      "userCount": 3,
      "fileCount": 156,
      "createdAt": "2025-01-01T00:00:00Z",
      "settings": null
    }
  ]
}
```

**FastAPI 實作**:
```python
@router.get("/", response_model=DepartmentListResponse)
async def get_departments(
    current_user: User = Depends(get_current_super_admin),  # 僅超級管理員
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有處室列表
    
    - 包含使用者數量和檔案數量統計
    - 僅超級管理員可存取
    """
    # 查詢所有處室
    query = await db.execute(
        select(Department).order_by(Department.name)
    )
    departments = query.scalars().all()
    
    # 為每個處室查詢統計資料
    result_items = []
    for dept in departments:
        # 使用者數量
        user_count = await db.scalar(
            select(func.count(User.id)).where(User.department_id == dept.id)
        )
        
        # 檔案數量
        file_count = await db.scalar(
            select(func.count(File.id)).where(File.department_id == dept.id)
        )
        
        dept_data = DepartmentResponse.from_orm(dept)
        dept_data.user_count = user_count
        dept_data.file_count = file_count
        result_items.append(dept_data)
    
    return DepartmentListResponse(items=result_items)
```

---

### GET /api/departments/{department_id}
取得單一處室詳細資訊

**前端對應**: `api/departments.js` → `getDepartmentById()`

```javascript
// 回應
{
  "id": 1,
  "name": "人事室",
  "description": "負責人事相關業務",
  "color": "red",
  "isActive": true,
  "userCount": 5,
  "fileCount": 234,
  "storageUsed": "2.5 GB",
  "createdAt": "2025-01-01T00:00:00Z",
  "updatedAt": "2025-11-12T10:00:00Z",
  "settings": {
    "maxFileSize": 52428800,
    "allowedExtensions": [".pdf", ".docx", ".txt"]
  }
}
```

**FastAPI 實作**:
```python
@router.get("/{department_id}", response_model=DepartmentDetailResponse)
async def get_department_by_id(
    department_id: int,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """取得單一處室的詳細資訊"""
    department = await db.get(Department, department_id)
    
    if not department:
        raise HTTPException(status_code=404, detail="處室不存在")
    
    # 統計資料
    user_count = await db.scalar(
        select(func.count(User.id)).where(User.department_id == department_id)
    )
    
    file_count = await db.scalar(
        select(func.count(File.id)).where(File.department_id == department_id)
    )
    
    storage_used = await db.scalar(
        select(func.sum(File.file_size)).where(File.department_id == department_id)
    ) or 0
    
    dept_data = DepartmentDetailResponse.from_orm(department)
    dept_data.user_count = user_count
    dept_data.file_count = file_count
    dept_data.storage_used = f"{storage_used / (1024**3):.2f} GB"
    
    return dept_data
```

---

### POST /api/departments
新增處室

**前端對應**: `api/departments.js` → `addDepartment()`

```javascript
// 請求
{
  "name": "總務處",
  "description": "負責總務相關業務",
  "color": "green"
}

// 回應
{
  "id": 3,
  "name": "總務處",
  "description": "負責總務相關業務",
  "color": "green",
  "userCount": 0,
  "fileCount": 0,
  "createdAt": "2025-11-12T10:00:00Z"
}
```

**FastAPI 實作**:
```python
@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    department_data: DepartmentCreate,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    新增處室
    
    - 檢查處室名稱是否重複
    - 自動建立預設分類（未分類）
    """
    # 檢查名稱是否重複
    existing = await db.execute(
        select(Department).where(Department.name == department_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="處室名稱已存在")
    
    # 建立處室
    department = Department(
        name=department_data.name,
        description=department_data.description,
        color=department_data.color or 'blue',
        is_active=True
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    
    # 自動建立預設「未分類」分類
    default_category = Category(
        name="未分類",
        color="gray",
        department_id=department.id
    )
    db.add(default_category)
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="department",
        entity_id=department.id,
        description=f"建立處室: {department.name}"
    )
    
    return DepartmentResponse.from_orm(department)
```

---

### PUT /api/departments/{department_id}
更新處室

**前端對應**: `api/departments.js` → `updateDepartment()`

```javascript
// 請求
{
  "name": "總務處（更新）",
  "description": "更新後的描述",
  "color": "green",
  "isActive": true
}

// 回應
{
  "message": "處室更新成功"
}
```

**FastAPI 實作**:
```python
@router.put("/{department_id}")
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新處室資訊"""
    department = await db.get(Department, department_id)
    
    if not department:
        raise HTTPException(status_code=404, detail="處室不存在")
    
    # 如果更新名稱，檢查是否重複
    if department_data.name and department_data.name != department.name:
        existing = await db.execute(
            select(Department).where(
                Department.name == department_data.name,
                Department.id != department_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="處室名稱已存在")
        department.name = department_data.name
    
    # 更新其他欄位
    if department_data.description is not None:
        department.description = department_data.description
    if department_data.color:
        department.color = department_data.color
    if department_data.is_active is not None:
        department.is_active = department_data.is_active
    
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="department",
        entity_id=department_id,
        description=f"更新處室: {department.name}"
    )
    
    return {"message": "處室更新成功"}
```

---

### DELETE /api/departments/{department_id}
刪除處室

**前端對應**: `api/departments.js` → `deleteDepartment()`

```javascript
// 回應
{
  "message": "處室刪除成功"
}
```

**FastAPI 實作**:
```python
@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除處室
    
    - 檢查是否有使用者屬於該處室
    - 檢查是否有檔案屬於該處室
    - 使用級聯刪除處理相關資料
    """
    department = await db.get(Department, department_id)
    
    if not department:
        raise HTTPException(status_code=404, detail="處室不存在")
    
    # 檢查是否有使用者
    user_count = await db.scalar(
        select(func.count(User.id)).where(User.department_id == department_id)
    )
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此處室下還有 {user_count} 個使用者，無法刪除"
        )
    
    # 檢查是否有檔案
    file_count = await db.scalar(
        select(func.count(File.id)).where(File.department_id == department_id)
    )
    if file_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"此處室下還有 {file_count} 個檔案，無法刪除"
        )
    
    # 刪除處室（級聯刪除分類等相關資料）
    await db.delete(department)
    await db.commit()
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="delete",
        entity_type="department",
        entity_id=department_id,
        description=f"刪除處室: {department.name}"
    )
    
    return {"message": "處室刪除成功"}
```

---

### GET /api/departments/{department_id}/stats
取得處室統計資料

**前端對應**: `api/departments.js` → `getDepartmentStats()`

```javascript
// 回應
{
  "departmentName": "人事室",
  "totalFiles": 234,
  "totalUsers": 5,
  "filesByCategory": [
    {
      "categoryName": "人事規章",
      "count": 45,
      "percentage": 19.2
    },
    {
      "categoryName": "請假相關",
      "count": 32,
      "percentage": 13.7
    }
  ],
  "recentActivities": [
    {
      "id": 1001,
      "username": "張三",
      "action": "upload",
      "description": "上傳檔案: 人事規章.pdf",
      "createdAt": "2025-11-12T14:30:00Z"
    }
  ],
  "storageUsed": "2.5 GB",
  "activeUsers": 4
}
```

**FastAPI 實作**:
```python
@router.get("/{department_id}/stats", response_model=DepartmentStatsResponse)
async def get_department_stats(
    department_id: int,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    取得處室統計資料
    
    - 檔案和使用者數量
    - 各分類的檔案分布
    - 最近的活動記錄
    - 儲存空間使用
    """
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="處室不存在")
    
    # 1. 總檔案數
    total_files = await db.scalar(
        select(func.count(File.id)).where(File.department_id == department_id)
    )
    
    # 2. 總使用者數
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.department_id == department_id)
    )
    
    # 3. 各分類檔案分布
    category_query = await db.execute(
        select(
            Category.name,
            func.count(File.id).label('count')
        )
        .outerjoin(File, File.category_id == Category.id)
        .where(Category.department_id == department_id)
        .group_by(Category.name)
        .order_by(desc('count'))
    )
    
    files_by_category = []
    for row in category_query:
        if total_files > 0:
            percentage = (row.count / total_files) * 100
        else:
            percentage = 0
        files_by_category.append({
            "category_name": row.name,
            "count": row.count,
            "percentage": round(percentage, 1)
        })
    
    # 4. 最近活動（最近 10 筆）
    recent_activities_query = await db.execute(
        select(Activity)
        .where(Activity.department_id == department_id)
        .order_by(desc(Activity.created_at))
        .limit(10)
        .options(joinedload(Activity.user))
    )
    recent_activities = recent_activities_query.scalars().all()
    
    # 5. 儲存空間使用
    storage_used = await db.scalar(
        select(func.sum(File.file_size)).where(File.department_id == department_id)
    ) or 0
    
    # 6. 活躍使用者數（最近 30 天有登入）
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_users = await db.scalar(
        select(func.count(User.id)).where(
            User.department_id == department_id,
            User.last_login >= thirty_days_ago
        )
    )
    
    return DepartmentStatsResponse(
        department_name=department.name,
        total_files=total_files,
        total_users=total_users,
        files_by_category=files_by_category,
        recent_activities=[ActivitySchema.from_orm(a) for a in recent_activities],
        storage_used=f"{storage_used / (1024**3):.2f} GB",
        active_users=active_users
    )
```

**Schema 定義**:
```python
# app/schemas/department.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DepartmentBase(BaseModel):
    """處室基礎 Schema"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = "blue"

class DepartmentCreate(DepartmentBase):
    """建立處室"""
    pass

class DepartmentUpdate(BaseModel):
    """更新處室（所有欄位可選）"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentResponse(DepartmentBase):
    """處室回應"""
    id: int
    user_count: int = 0
    file_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

class DepartmentDetailResponse(DepartmentResponse):
    """處室詳細資訊"""
    is_active: bool
    storage_used: str
    updated_at: datetime
    settings: Optional[Dict[str, Any]] = None

class DepartmentListResponse(BaseModel):
    """處室列表回應"""
    items: List[DepartmentResponse]

class CategoryStatsItem(BaseModel):
    """分類統計項目"""
    category_name: str
    count: int
    percentage: float

class DepartmentStatsResponse(BaseModel):
    """處室統計資料"""
    department_name: str
    total_files: int
    total_users: int
    files_by_category: List[CategoryStatsItem]
    recent_activities: List[Any]  # ActivitySchema
    storage_used: str
    active_users: int
```

---

## 8. 系統設定模組 (Settings)

### GET /api/settings
取得系統設定

**前端對應**: `api/settings.js` → `getSettings()`

```javascript
// 回應
{
  "system": {
    "siteName": "知識庫管理系統",
    "maxFileSize": 52428800,
    "allowedExtensions": [".pdf", ".docx", ".txt", ".xlsx"],
    "enableAutoBackup": true,
    "backupSchedule": "0 2 * * *"
  },
  "storage": {
    "storageQuota": 10737418240,
    "storageUsed": 2684354560,
    "storageWarningThreshold": 80
  },
  "security": {
    "sessionTimeout": 3600,
    "passwordMinLength": 8,
    "enableTwoFactor": false
  },
  "rag": {
    "embeddingModel": "text-embedding-ada-002",
    "chunkSize": 1000,
    "chunkOverlap": 200,
    "topK": 5
  }
}
```

**FastAPI 實作**:
```python
@router.get("/", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_super_admin),  # 僅超級管理員
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    取得系統設定
    
    - 從 Redis 快取讀取（如果有的話）
    - 否則從資料庫讀取
    """
    # 嘗試從 Redis 讀取快取
    cached_settings = await redis.get("system:settings")
    if cached_settings:
        return json.loads(cached_settings)
    
    # 從資料庫讀取
    settings_query = await db.execute(
        select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)
    )
    settings = settings_query.scalars().all()
    
    # 按類別組織設定
    organized_settings = {
        "system": {},
        "storage": {},
        "security": {},
        "rag": {}
    }
    
    for setting in settings:
        if setting.category in organized_settings:
            organized_settings[setting.category][setting.key] = setting.value
    
    # 快取到 Redis（1小時）
    await redis.setex(
        "system:settings",
        3600,
        json.dumps(organized_settings)
    )
    
    return SettingsResponse(**organized_settings)
```

---

### PUT /api/settings
更新系統設定

**前端對應**: `api/settings.js` → `updateSettings()`

```javascript
// 請求
{
  "system": {
    "siteName": "更新後的名稱",
    "maxFileSize": 104857600
  },
  "storage": {
    "storageQuota": 21474836480
  }
}

// 回應
{
  "message": "設定已儲存"
}
```

**FastAPI 實作**:
```python
@router.put("/")
async def update_settings(
    settings_data: SettingsUpdate,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    更新系統設定
    
    - 更新資料庫中的設定
    - 清除 Redis 快取
    - 記錄活動
    """
    updated_count = 0
    
    # 更新各類別設定
    for category, settings in settings_data.dict(exclude_unset=True).items():
        for key, value in settings.items():
            # 查找或建立設定
            setting = await db.scalar(
                select(SystemSetting).where(
                    SystemSetting.category == category,
                    SystemSetting.key == key
                )
            )
            
            if setting:
                setting.value = value
                setting.updated_by = current_user.id
            else:
                setting = SystemSetting(
                    category=category,
                    key=key,
                    value=value,
                    created_by=current_user.id
                )
                db.add(setting)
            
            updated_count += 1
    
    await db.commit()
    
    # 清除 Redis 快取
    await redis.delete("system:settings")
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="settings",
        description=f"更新 {updated_count} 項系統設定"
    )
    
    return {"message": "設定已儲存"}
```

---

### GET /api/backups/history
取得備份歷史記錄

**前端對應**: `api/settings.js` → `getBackupHistory()`

```javascript
// 回應
{
  "items": [
    {
      "id": 1,
      "date": "2025-11-12T02:00:00Z",
      "size": "1.2 GB",
      "sizeBytes": 1288490188,
      "type": "automatic",
      "status": "completed",
      "createdBy": "系統自動備份",
      "filePath": "/backups/backup_20251112_020000.zip"
    },
    {
      "id": 2,
      "date": "2025-11-11T15:30:00Z",
      "size": "1.1 GB",
      "sizeBytes": 1181116006,
      "type": "manual",
      "status": "completed",
      "createdBy": "admin",
      "filePath": "/backups/backup_20251111_153000.zip"
    }
  ]
}
```

**FastAPI 實作**:
```python
@router.get("/history", response_model=BackupListResponse)
async def get_backup_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    取得備份歷史記錄
    
    - 列出所有備份檔案
    - 包含備份大小、類型、狀態
    """
    query = await db.execute(
        select(Backup)
        .order_by(desc(Backup.created_at))
        .limit(limit)
        .options(joinedload(Backup.creator))
    )
    backups = query.scalars().unique().all()
    
    backup_list = []
    for backup in backups:
        # 計算檔案大小
        size_bytes = 0
        if os.path.exists(backup.file_path):
            size_bytes = os.path.getsize(backup.file_path)
        
        backup_list.append({
            "id": backup.id,
            "date": backup.created_at,
            "size": f"{size_bytes / (1024**3):.2f} GB",
            "size_bytes": size_bytes,
            "type": backup.backup_type,
            "status": backup.status,
            "created_by": backup.creator.username if backup.creator else "系統自動備份",
            "file_path": backup.file_path
        })
    
    return BackupListResponse(items=backup_list)
```

---

### POST /api/backups/create
建立手動備份

**前端對應**: `api/settings.js` → `createBackup()`

```javascript
// 回應
{
  "message": "備份建立成功",
  "backupId": 3,
  "estimatedTime": "5-10 分鐘"
}
```

**FastAPI 實作**:
```python
@router.post("/create")
async def create_backup(
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    建立手動備份
    
    - 使用背景任務執行備份
    - 備份包含資料庫和檔案
    """
    # 檢查是否有正在進行的備份
    ongoing_backup = await db.scalar(
        select(Backup).where(Backup.status == "in_progress")
    )
    if ongoing_backup:
        raise HTTPException(
            status_code=400,
            detail="已有備份任務正在進行中，請稍後再試"
        )
    
    # 建立備份記錄
    backup_time = datetime.now()
    backup_filename = f"backup_{backup_time.strftime('%Y%m%d_%H%M%S')}.zip"
    backup_path = os.path.join(settings.BACKUP_DIR, backup_filename)
    
    backup = Backup(
        file_path=backup_path,
        backup_type="manual",
        status="in_progress",
        created_by=current_user.id
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)
    
    # 觸發背景任務
    background_tasks.add_task(
        perform_backup_task,
        backup_id=backup.id,
        backup_path=backup_path
    )
    
    # 記錄活動
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="backup",
        entity_id=backup.id,
        description="建立手動備份"
    )
    
    return {
        "message": "備份建立成功",
        "backup_id": backup.id,
        "estimated_time": "5-10 分鐘"
    }
```

---

### POST /api/backups/{backup_id}/restore
還原備份

**前端對應**: `api/settings.js` → `restoreBackup()`

```javascript
// 回應
{
  "message": "備份還原成功，系統將在 5 秒後重新啟動"
}
```

**FastAPI 實作**:
```python
@router.post("/{backup_id}/restore")
async def restore_backup(
    backup_id: int,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    還原備份
    
    - 驗證備份檔案完整性
    - 執行還原操作
    - 需要重啟系統
    """
    # 取得備份記錄
    backup = await db.get(Backup, backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="備份不存在")
    
    if backup.status != "completed":
        raise HTTPException(status_code=400, detail="此備份無法使用")
    
    # 檢查備份檔案是否存在
    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="備份檔案不存在")
    
    # 記錄還原活動（在還原前記錄）
    await activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="restore",
        entity_type="backup",
        entity_id=backup_id,
        description=f"還原備份: {backup.file_path}"
    )
    await db.commit()
    
    # 執行還原（這會停止當前的請求處理）
    try:
        await perform_restore_task(backup.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"備份還原失敗: {str(e)}"
        )
    
    return {
        "message": "備份還原成功，系統將在 5 秒後重新啟動"
    }
```

---

### GET /api/system/info
取得系統資訊

**前端對應**: `api/settings.js` → `getSystemInfo()`

```javascript
// 回應
{
  "version": "1.0.0",
  "uptime": "15天 6小時 32分",
  "uptimeSeconds": 1327920,
  "cpuUsage": 35.2,
  "memoryUsage": 68.5,
  "databaseSize": "850 MB",
  "cacheSize": "120 MB",
  "apiRequests": 125680,
  "errorRate": 0.02,
  "storage": {
    "total": "10 GB",
    "used": "2.5 GB",
    "available": "7.5 GB",
    "percentage": 25
  }
}
```

**FastAPI 實作**:
```python
@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    取得系統資訊
    
    - CPU 和記憶體使用率
    - 資料庫大小
    - API 請求統計
    - 儲存空間使用
    """
    import psutil
    
    # 1. 系統資源
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    
    # 2. 系統運行時間
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_str = format_uptime(uptime_seconds)
    
    # 3. 資料庫大小
    db_size_query = await db.execute(
        text("SELECT pg_database_size(current_database())")
    )
    db_size_bytes = db_size_query.scalar()
    db_size = f"{db_size_bytes / (1024**2):.0f} MB"
    
    # 4. Redis 快取大小
    redis_info = await redis.info("memory")
    cache_size_bytes = redis_info.get("used_memory", 0)
    cache_size = f"{cache_size_bytes / (1024**2):.0f} MB"
    
    # 5. API 請求統計（從 Redis 計數器）
    api_requests = int(await redis.get("stats:api_requests") or 0)
    error_count = int(await redis.get("stats:api_errors") or 0)
    error_rate = (error_count / api_requests * 100) if api_requests > 0 else 0
    
    # 6. 儲存空間
    storage_path = settings.UPLOAD_DIR
    disk_usage = psutil.disk_usage(storage_path)
    storage_info = {
        "total": f"{disk_usage.total / (1024**3):.0f} GB",
        "used": f"{disk_usage.used / (1024**3):.1f} GB",
        "available": f"{disk_usage.free / (1024**3):.1f} GB",
        "percentage": disk_usage.percent
    }
    
    return SystemInfoResponse(
        version="1.0.0",
        uptime=uptime_str,
        uptime_seconds=int(uptime_seconds),
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        database_size=db_size,
        cache_size=cache_size,
        api_requests=api_requests,
        error_rate=round(error_rate, 2),
        storage=storage_info
    )

def format_uptime(seconds: int) -> str:
    """格式化運行時間"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{int(days)}天 {int(hours)}小時 {int(minutes)}分"
```

**Schema 定義**:
```python
# app/schemas/settings.py
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class SystemSettings(BaseModel):
    """系統設定"""
    site_name: str
    max_file_size: int
    allowed_extensions: List[str]
    enable_auto_backup: bool
    backup_schedule: str

class StorageSettings(BaseModel):
    """儲存設定"""
    storage_quota: int
    storage_used: int
    storage_warning_threshold: int

class SecuritySettings(BaseModel):
    """安全設定"""
    session_timeout: int
    password_min_length: int
    enable_two_factor: bool

class RAGSettings(BaseModel):
    """RAG 設定"""
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int

class SettingsResponse(BaseModel):
    """設定回應"""
    system: SystemSettings
    storage: StorageSettings
    security: SecuritySettings
    rag: RAGSettings

class SettingsUpdate(BaseModel):
    """設定更新（所有欄位可選）"""
    system: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    rag: Optional[Dict[str, Any]] = None

class BackupItem(BaseModel):
    """備份項目"""
    id: int
    date: datetime
    size: str
    size_bytes: int
    type: str
    status: str
    created_by: str
    file_path: str

class BackupListResponse(BaseModel):
    """備份列表回應"""
    items: List[BackupItem]

class StorageInfo(BaseModel):
    """儲存空間資訊"""
    total: str
    used: str
    available: str
    percentage: float

class SystemInfoResponse(BaseModel):
    """系統資訊回應"""
    version: str
    uptime: str
    uptime_seconds: int
    cpu_usage: float
    memory_usage: float
    database_size: str
    cache_size: str
    api_requests: int
    error_rate: float
    storage: StorageInfo
```

**資料庫模型**:
```python
# app/models/system_setting.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base, TimestampMixin

class SystemSetting(Base, TimestampMixin):
    """系統設定"""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)  # system, storage, security, rag
    key = Column(String(100), nullable=False)
    value = Column(JSONB, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    updated_by = Column(Integer, ForeignKey('users.id'))

# app/models/backup.py
class Backup(Base, TimestampMixin):
    """備份記錄"""
    __tablename__ = 'backups'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    backup_type = Column(String(20), nullable=False)  # manual, automatic
    status = Column(String(20), default='in_progress')  # in_progress, completed, failed
    created_by = Column(Integer, ForeignKey('users.id'))
```

---

## 9. 統計資料模組 (Statistics)

此模組整合了系統的各項統計資料，供儀表板使用。

### GET /api/statistics
取得系統統計資料（已在活動記錄模組說明）

**路由位置**: 建議放在 `app/api/v1/statistics.py`

**前端對應**: `api/activities.js` → `getStatistics()`

```javascript
// 回應
{
  "totalFiles": 234,
  "filesByCategory": {
    "人事規章": 45,
    "請假相關": 32,
    "薪資福利": 28
  },
  "monthlyQueries": [120, 145, 167, 189, 203],
  "systemStatus": "healthy",
  "storageUsed": "2.5 GB",
  "storageTotal": "10 GB"
}
```

**FastAPI 完整實作**:
```python
# app/api/v1/statistics.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.category import Category
from app.schemas.statistics import StatisticsResponse

router = APIRouter()

@router.get("/", response_model=StatisticsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得統計資料（自動過濾處室）
    
    - 總檔案數
    - 各分類檔案數
    - 儲存空間使用
    - 系統狀態
    """
    # 1. 總檔案數
    total_files = await db.scalar(
        select(func.count(File.id))
        .where(File.department_id == current_user.department_id)
    )
    
    # 2. 各分類檔案數
    category_query = await db.execute(
        select(Category.name, func.count(File.id).label('count'))
        .outerjoin(File, File.category_id == Category.id)
        .where(Category.department_id == current_user.department_id)
        .group_by(Category.name)
    )
    files_by_category = {row.name: row.count for row in category_query}
    
    # 3. 儲存空間使用
    storage_used_bytes = await db.scalar(
        select(func.sum(File.file_size))
        .where(File.department_id == current_user.department_id)
    ) or 0
    storage_used_gb = storage_used_bytes / (1024 ** 3)
    
    # 4. 月度查詢數（此處為示例，實際需從查詢記錄表獲取）
    monthly_queries = []  # TODO: 實作查詢記錄統計
    
    return StatisticsResponse(
        total_files=total_files,
        files_by_category=files_by_category,
        monthly_queries=monthly_queries,
        system_status="healthy",
        storage_used=f"{storage_used_gb:.2f} GB",
        storage_total="10 GB"  # 從系統設定讀取
    )
```

**Schema 定義**:
```python
# app/schemas/statistics.py
from pydantic import BaseModel
from typing import Dict, List

class StatisticsResponse(BaseModel):
    """統計資料回應"""
    total_files: int
    files_by_category: Dict[str, int]
    monthly_queries: List[int]
    system_status: str
    storage_used: str
    storage_total: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_files": 234,
                "files_by_category": {
                    "人事規章": 45,
                    "請假相關": 32
                },
                "monthly_queries": [120, 145, 167],
                "system_status": "healthy",
                "storage_used": "2.5 GB",
                "storage_total": "10 GB"
            }
        }
```

**主應用程式註冊**:
```python
# app/main.py
from app.api.v1 import statistics

app.include_router(statistics.router, prefix="/api/statistics", tags=["統計資料"])
```

---

## API 路由總覽

以下是所有 API 路由的完整列表，按模組分類：

| 模組 | 路由前綴 | 端點數 | 說明 | 權限需求 |
|------|---------|--------|------|---------|
| 認證 | `/api/auth` | 3 | login, logout, verify | Public/User |
| 檔案管理 | `/api/files` | 7 | CRUD + upload + download + check-duplicates | User/Admin |
| 分類管理 | `/api/categories` | 4 | GET, POST, DELETE, stats | User/Admin |
| 活動記錄 | `/api/activities` | 2 | GET (user), GET /all (super admin) | User/SuperAdmin |
| 批次上傳 | `/api/upload` | 5 | batch, progress, tasks (CRUD) | User/Admin |
| 使用者管理 | `/api/users` | 4 | CRUD (完整實作) | SuperAdmin |
| 處室管理 | `/api/departments` | 6 | CRUD + stats | SuperAdmin |
| 系統設定 | `/api/settings` | 6 | settings, backups (CRUD), system/info | SuperAdmin |
| 統計資料 | `/api/statistics` | 1 | 儀表板統計資料 | User |

**總計**: 9 個模組，38 個 API 端點

### 各模組詳細端點清單

#### 1. 認證模組 (3)
- POST `/api/auth/login`
- POST `/api/auth/logout`
- GET `/api/auth/verify`

#### 2. 檔案管理模組 (7)
- GET `/api/files` - 檔案列表（分頁、搜尋、篩選）
- POST `/api/files/upload` - 上傳單一檔案
- POST `/api/files/check-duplicates` - 檢查重複檔案
- GET `/api/files/{id}` - 取得檔案詳情
- PUT `/api/files/{id}` - 更新檔案資訊
- DELETE `/api/files/{id}` - 刪除檔案
- GET `/api/files/{id}/download` - 下載檔案

#### 3. 分類管理模組 (4)
- GET `/api/categories` - 分類列表
- POST `/api/categories` - 新增分類
- DELETE `/api/categories/{id}` - 刪除分類
- GET `/api/categories/stats` - 分類統計

#### 4. 活動記錄模組 (2)
- GET `/api/activities` - 取得活動記錄（自動過濾處室）
- GET `/api/activities/all` - 取得所有處室活動（僅超級管理員）

#### 5. 批次上傳模組 (5)
- POST `/api/upload/batch` - 批次上傳檔案
- GET `/api/upload/progress/{task_id}` - 查詢上傳進度
- GET `/api/upload/tasks` - 取得使用者的上傳任務列表
- DELETE `/api/upload/tasks/{task_id}` - 刪除上傳任務記錄

#### 6. 使用者管理模組 (4)
- GET `/api/users` - 使用者列表
- POST `/api/users` - 新增使用者
- PUT `/api/users/{id}` - 更新使用者
- DELETE `/api/users/{id}` - 刪除使用者

#### 7. 處室管理模組 (6)
- GET `/api/departments` - 處室列表
- GET `/api/departments/{id}` - 處室詳情
- POST `/api/departments` - 新增處室
- PUT `/api/departments/{id}` - 更新處室
- DELETE `/api/departments/{id}` - 刪除處室
- GET `/api/departments/{id}/stats` - 處室統計

#### 8. 系統設定模組 (6)
- GET `/api/settings` - 取得系統設定
- PUT `/api/settings` - 更新系統設定
- GET `/api/backups/history` - 備份歷史
- POST `/api/backups/create` - 建立備份
- POST `/api/backups/{id}/restore` - 還原備份
- GET `/api/system/info` - 系統資訊

#### 9. 統計資料模組 (1)
- GET `/api/statistics` - 系統統計資料

---

## API 錯誤處理

### 標準錯誤格式
```json
{
  "detail": "錯誤訊息",
  "error_code": "FILE_TOO_LARGE",
  "status_code": 400
}
```

### HTTP 狀態碼
- **200**: 成功
- **201**: 建立成功
- **400**: 請求錯誤
- **401**: 未認證
- **403**: 無權限
- **404**: 資源不存在
- **413**: 檔案過大
- **500**: 伺服器錯誤

---

**下一步**: 閱讀 [05_FOLDER_STRUCTURE.md](./05_FOLDER_STRUCTURE.md) 了解專案結構
