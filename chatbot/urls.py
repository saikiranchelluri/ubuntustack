from django.urls import path
from chatbot.views import YoueAiChatbotView,GenerateChatIdView,ConversationHistoryView

urlpatterns = [
    path('v1/youe-ai/generate-chat-id/<user_id>/',GenerateChatIdView.as_view()),
    path('v1/youe-ai/',YoueAiChatbotView.as_view()),
    path('v1/youe-ai/conversation-history/<user_id>/',ConversationHistoryView.as_view()),
    
]