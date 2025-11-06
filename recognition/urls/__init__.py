# URLs package - combines all URL sub-modules into a single urlpatterns list

from .auth import urlpatterns as auth_urls
from .dashboard import urlpatterns as dashboard_urls
from .attendance import urlpatterns as attendance_urls
from .face import urlpatterns as face_urls

urlpatterns = []
urlpatterns += dashboard_urls
urlpatterns += auth_urls
urlpatterns += attendance_urls
urlpatterns += face_urls
