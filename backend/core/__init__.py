"""
core - 后端核心业务逻辑层

提供服务类和数据模型，与 API 路由层分离。
"""

from .news_service import NewsService
from .admin_service import get_users, get_user_detail, update_user_subscription, get_feedbacks, reply_feedback
from .auth_service import (
    hash_password, generate_token, validate_phone, validate_email,
    generate_code, get_user_by_token,
    send_phone_code, send_email_code, send_reset_code,
    register_by_phone, login_by_phone_code, login_by_password,
    email_register, reset_password, logout,
    update_nickname, update_phone, update_email, update_password,
    get_user_full_info,
)
from .subscription_service import (
    get_subscription_plans, get_pay_method, generate_order_no,
    get_user_by_token as sub_get_user_by_token,
    create_subscription_order, get_order_status,
    parse_wechat_notify, process_wechat_notify,
    activate_subscription_direct, cancel_subscription,
    get_current_subscription,
    get_personal_qr_image_bytes,
    send_payment_notification_email,
)
from .feedback_service import (
    get_user_by_token as fb_get_user_by_token,
    submit_feedback, get_comments, add_comment,
    update_comment, delete_comment,
)

__all__ = [
    "NewsService",
    # admin
    "get_users", "get_user_detail", "update_user_subscription", "get_feedbacks", "reply_feedback",
    # auth
    "hash_password", "generate_token", "validate_phone", "validate_email",
    "generate_code", "get_user_by_token",
    "send_phone_code", "send_email_code", "send_reset_code",
    "register_by_phone", "login_by_phone_code", "login_by_password",
    "email_register", "reset_password", "logout",
    "update_nickname", "update_phone", "update_email", "update_password",
    "get_user_full_info",
    # subscription
    "get_subscription_plans", "get_pay_method", "generate_order_no",
    "create_subscription_order", "get_order_status",
    "parse_wechat_notify", "process_wechat_notify",
    "activate_subscription_direct", "cancel_subscription",
    "get_current_subscription",
    "get_personal_qr_image_bytes", "send_payment_notification_email",
    # feedback
    "submit_feedback", "get_comments", "add_comment",
    "update_comment", "delete_comment",
]