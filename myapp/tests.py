from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Collection, Item, Profile, ItemReview
from django.utils import timezone

class ModelTests(TestCase):
    def setUp(self):
        # Test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Test collection
        self.collection = Collection.objects.create(
            title='Test Collection',
            description='Test Description',
            created_by=self.user
        )
        
        # Test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Item Description',
            created_by=self.user,
            location='Test Location',
            identifier='TEST001'
        )
        
        # Test profile
        self.profile = Profile.objects.create(
            user=self.user
        )

    def test_collection_creation(self):
        # Test for creating a collection
        self.assertEqual(self.collection.title, 'Test Collection')
        self.assertEqual(self.collection.description, 'Test Description')
        self.assertEqual(self.collection.created_by, self.user)

    def test_item_creation(self):
        # Test for creating an item
        self.assertEqual(self.item.title, 'Test Item')
        self.assertEqual(self.item.description, 'Test Item Description')
        self.assertEqual(self.item.created_by, self.user)
        self.assertEqual(self.item.location, 'Test Location')
        self.assertEqual(self.item.identifier, 'TEST001')

    def test_profile_creation(self):
        #Test for creating a profile
        self.assertEqual(self.profile.user, self.user)

    def test_item_review(self):
        # Test for creating an item review"""
        review = ItemReview.objects.create(
            item=self.item,
            user=self.user,
            rating=5,
            comment='I love this item!'
        )
        self.assertEqual(review.item, self.item)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'I love this item!')

    def test_collection_and_items(self):
        # Test for adding items to a collection
        self.collection.items.add(self.item)
        self.assertIn(self.item, self.collection.items.all())
        self.assertEqual(self.collection.items.count(), 1)