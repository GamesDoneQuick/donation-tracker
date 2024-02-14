from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import VideoLinkSerializer


class TestVideoLinkSerializer(APITestCase):
    def setUp(self):
        super().setUp()
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.run = randgen.generate_run(self.rand, event=self.event)
        self.run.save()
        self.link_type = models.VideoLinkType.objects.create(name='youtube')
        self.link1 = models.VideoLink.objects.create(
            run=self.run, link_type=self.link_type, url='http://example.com/youtube'
        )

    def test_serializer(self):
        data = VideoLinkSerializer(self.link1).data
        self.assertEqual(
            data,
            {
                'id': self.link1.id,
                'link_type': self.link_type.name,
                'url': self.link1.url,
            },
        )
