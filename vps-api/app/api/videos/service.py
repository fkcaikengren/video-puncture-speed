import os
import uuid
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import UnprocessableEntityException, InternalServerException

from app.core.tempfile_manager import TempfileManager
from app.core.video import transcode_video, extract_first_frame, get_video_metadata
from app.core.storage import storage
from app.core.logging import get_logger
from app.api.videos.repository import VideoRepository
from app.api.comparisons.repository import ComparisonRepository
from app.api.videos.schemas import VideoCreate, VideoResponse, VideoDetailResponse, UploadResponse, VideoListResponse, AnalysisResponse, AnalysisResultResponse
from app.api.videos.enums import VideoStatus
from app.api.videos.models import Video, AnalysisResult

from video_work.core import analyse_video

logger = get_logger(__name__)
DEFAULT_CATEGORY_ID = 1

class VideoService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = VideoRepository(session)
        self.comparison_repo = ComparisonRepository(session)

    async def process_video_upload(self, file: UploadFile, user_id: uuid.UUID, username: str = None, title: str = None, category_id: int = DEFAULT_CATEGORY_ID) -> UploadResponse:
        """
        处理视频上传、转码和存储的核心逻辑
        """
        # Generate a unique object name for storage
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        output_object_name = f"videos/{uuid.uuid4()}.mp4"

        logger.info(f"Starting video upload process for file: {file.filename}")

        thumbnail_object_name: str | None = None
        duration: int | None = None
        size: int | None = None
        fps: int | None = None

        try:
            # 1. 视频文件落盘到临时目录
            with TempfileManager.create_temp_file(suffix=file_ext) as temp_input_path:
                logger.debug(f"Saving upload to temp file: {temp_input_path}")
                await file.seek(0)
                with open(temp_input_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # 2. 视频转码
                with TempfileManager.create_temp_file(suffix=".mp4") as temp_output_path:
                    logger.info(f"Transcoding video to: {temp_output_path}")
                    try:
                        transcode_video(temp_input_path, temp_output_path)
                    except Exception as e:
                        logger.error(f"Transcoding failed: {e}")
                        raise UnprocessableEntityException(detail=f"Transcoding failed: {str(e)}")
                    try:
                        metadata = get_video_metadata(temp_output_path)
                        duration = metadata.get("duration")
                        size = metadata.get("size")
                        fps = metadata.get("fps")
                    except Exception as e:
                        logger.error(f"Metadata extraction failed: {e}")

                    try:
                        with TempfileManager.create_temp_file(suffix=".png") as temp_thumb_path:
                            extract_first_frame(temp_output_path, temp_thumb_path)
                            thumbnail_object_name = f"thumbnails/{uuid.uuid4()}.png"
                            logger.info(f"Uploading thumbnail to storage: {thumbnail_object_name}")
                            storage.upload_file(
                                file_path=temp_thumb_path,
                                object_name=thumbnail_object_name,
                                content_type="image/png",
                            )
                    except Exception as e:
                        logger.error(f"Thumbnail generation or upload failed: {e}")

                    logger.info(f"Uploading transcoded video to storage: {output_object_name}")
                    try:
                        storage.upload_file(
                            file_path=temp_output_path,
                            object_name=output_object_name,
                            content_type="video/mp4",
                        )
                    except Exception as e:
                        logger.error(f"Storage upload failed: {e}")
                        raise InternalServerException(detail=f"Storage upload failed: {str(e)}")
        
            # 保存视频元数据到DB
            video_data = VideoCreate(
                title=title or file.filename,
                raw_path=output_object_name,
                category_id=category_id or DEFAULT_CATEGORY_ID,
                thumbnail_path=thumbnail_object_name,
                duration=duration,
                size=size,
                fps=fps,
                uploader=username
            )
            video = await self.repository.create_video(video_data, user_id)
            
            raw_url = storage.get_url(video.raw_path)
            thumbnail_url = storage.get_url(video.thumbnail_path) if video.thumbnail_path else None
            
            return UploadResponse(
                id=video.id,
                status=video.status,
                raw_url=raw_url,
                thumbnail_url=thumbnail_url,
                created_at=video.created_at
            )

        except Exception as e:
            logger.error(f"Unexpected error during video upload: {e}")
            raise InternalServerException(detail="Internal server error during video processing")

    async def get_videos(self, user_id: uuid.UUID, page: int, page_size: int, keyword: str = None, category_id: int = None, status: int = None) -> VideoListResponse:
        videos, total = await self.repository.get_videos(user_id, page, page_size, keyword, category_id, status)
        items = [VideoResponse.model_validate(v) for v in videos]
        return VideoListResponse(items=items, total=total, page=page, page_size=page_size)

    async def get_candidates(self, user_id: uuid.UUID, page: int, page_size: int, keyword: str = None, category_id: int = None) -> VideoListResponse:
        videos, total = await self.repository.get_candidates(user_id, page, page_size, keyword, category_id)
        items = [VideoResponse.model_validate(v) for v in videos]
        return VideoListResponse(items=items, total=total, page=page, page_size=page_size)

    async def get_video_detail(self, video_id: uuid.UUID) -> VideoDetailResponse:
        video = await self.repository.get_video(video_id)
        return VideoDetailResponse.model_validate(video)

    async def delete_video(self, video_id: uuid.UUID):
        # 1. Get video with all relations to ensure we can clean up files
        video = await self.repository.get_video_with_analysis_result(video_id)
        
        # 2. Check if comparison reports exist
        if video.comparison_reports:
            raise UnprocessableEntityException(detail="检测到存在对比分析记录，无法删除")

        # 3. Delete analysis files if present
        if video.analysis_result and video.analysis_result.marked_path:
            try:
                storage.delete_file(video.analysis_result.marked_path)
            except Exception as e:
                logger.warning(f"Failed to delete analysis marked file {video.analysis_result.marked_path}: {e}")

        # 4. Delete video files
        if video.raw_path:
            try:
                storage.delete_file(video.raw_path)
            except Exception as e:
                logger.warning(f"Failed to delete raw file {video.raw_path}: {e}")
                
        if video.thumbnail_path:
            try:
                storage.delete_file(video.thumbnail_path)
            except Exception as e:
                logger.warning(f"Failed to delete thumbnail {video.thumbnail_path}: {e}")
            
        # 5. Delete DB records
        # Analysis result will be deleted by CASCADE on foreign key
        await self.repository.delete_video_record(video)
        return True

    async def get_analysis(self, video_id: uuid.UUID) -> AnalysisResponse:
        video_detail = await self.get_video_detail(video_id)
        analysis = await self.repository.get_analysis_result(video_id)
        
        analysis_resp = None
        if analysis:
            marked_url = storage.get_url(analysis.marked_path) if analysis.marked_path else None
            a_dict = analysis.__dict__.copy()
            a_dict['marked_url'] = marked_url
            analysis_resp = AnalysisResultResponse.model_validate(a_dict)
            
        return AnalysisResponse(video=video_detail, analysis=analysis_resp)


    async def process_video_analysis(self, video_id: uuid.UUID) -> None:
        video = await self.repository.get_video_with_analysis_result(video_id)
        video.status = int(VideoStatus.PROCESSING)
        await self.session.commit()
        await self.session.refresh(video)

        def status_callback(payload: dict) -> None:
            status = payload.get("status")
            logger.info("video analysis status", extra={"status": status, "video_id": str(video_id)})

        logger.info("start downloading video raw file ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})


        try:
            with storage.download_tmp(video.raw_path) as temp_video_path:
                
                logger.info("end downloading video raw file ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})
                analysed_video_name = f"videos/{uuid.uuid4()}.mp4"
                fps = int(video.fps) if video.fps else None
                if not fps or fps <= 0:
                    metadata = get_video_metadata(temp_video_path)
                    fps = int(metadata.get("fps") or 0)
                    if fps <= 0:
                        raise UnprocessableEntityException(detail="视频 FPS 缺失，无法换算预测时间")

                with TempfileManager.create_temp_file(suffix=".mp4") as temp_save_path:
                    logger.info("start analysing video ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})
                    # 调用模型分析视频
                    output = analyse_video(temp_video_path, temp_save_path, status_callback=status_callback)
                    logger.info("end analysing video ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})
                    try:
                        logger.info("start uploading analysed video ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})   
                        # 上传分析视频到storage
                        storage.upload_file(
                                file_path=temp_save_path,
                                object_name=analysed_video_name,
                                content_type="video/mp4",
                            )
                        logger.info("end uploading analysed video ...", extra={"video_id": str(video_id), "raw_path": video.raw_path})   
                    except Exception as e:
                        analysed_video_name = ''
                        logger.error(f"Failed to save analysed video {video_id}: {e}")
                    

                start_time = round(output.predict_start / fps, 3)
                end_time = round(output.predict_end / fps, 3)
                curve_data = [
                    {"t": round(frame_idx / fps, 2), "v": float(v)}
                    for frame_idx, v in zip(output.instantaneous_speed_indexes, output.instantaneous_speeds)
                ]

                if video.analysis_result:
                    ar = video.analysis_result
                    ar.marked_path = analysed_video_name
                    ar.start_time = start_time
                    ar.end_time = end_time
                    ar.init_speed = float(output.init_speed)
                    ar.avg_speed = float(output.avg_speed)
                    ar.curve_data = curve_data
                    ar.processed_at = datetime.utcnow()
                else:
                    video.analysis_result = AnalysisResult(
                        video_id=video.id,
                        marked_path=analysed_video_name,
                        start_time=start_time,
                        end_time=end_time,
                        init_speed=float(output.init_speed),
                        avg_speed=float(output.avg_speed),
                        curve_data=curve_data,
                        processed_at=datetime.utcnow(),
                    )

                video.status = int(VideoStatus.COMPLETED)
                video.error_log = None
                video.fps = fps
                await self.session.commit()
        except Exception as e:
            video.status = int(VideoStatus.FAILED)
            video.error_log = str(e)
            await self.session.commit()
            raise
