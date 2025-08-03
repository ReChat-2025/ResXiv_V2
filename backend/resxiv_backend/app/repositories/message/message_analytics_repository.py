"""
Message Analytics Repository - L6 Engineering Standards
Focused on message analytics, statistics, and performance-optimized queries.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo

from app.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class MessageAnalyticsRepository:
    """
    Analytics repository for message statistics and aggregations.
    Single Responsibility: Message analytics and performance-optimized queries.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.db: AsyncIOMotorDatabase = db_manager.mongodb_database
        self.messages: AsyncIOMotorCollection = self.db.messages
        self.conversation_metadata: AsyncIOMotorCollection = self.db.conversation_metadata
    
    async def get_conversation_stats(
        self,
        conversation_id: uuid.UUID,
        time_range: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive conversation statistics.
        
        Args:
            conversation_id: Conversation UUID
            time_range: Optional time range in days
            
        Returns:
            Conversation statistics
        """
        try:
            # Build match stage
            match_stage = {
                "conversation_id": str(conversation_id),
                "deleted_at": None
            }
            
            if time_range:
                cutoff_date = datetime.utcnow() - timedelta(days=time_range)
                match_stage["created_at"] = {"$gte": cutoff_date}
            
            # Optimized aggregation pipeline
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": None,
                        "total_messages": {"$sum": 1},
                        "unique_senders": {"$addToSet": "$sender_id"},
                        "message_types": {"$push": "$type"},
                        "first_message": {"$min": "$created_at"},
                        "last_message": {"$max": "$created_at"},
                        "total_reactions": {"$sum": {"$size": "$reactions"}},
                        "edited_messages": {
                            "$sum": {"$cond": [{"$eq": ["$edited", True]}, 1, 0]}
                        }
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "total_messages": 1,
                        "unique_sender_count": {"$size": "$unique_senders"},
                        "unique_senders": 1,
                        "message_type_distribution": {
                            "$arrayToObject": {
                                "$map": {
                                    "input": {"$setUnion": ["$message_types"]},
                                    "in": {
                                        "k": "$$this",
                                        "v": {
                                            "$size": {
                                                "$filter": {
                                                    "input": "$message_types",
                                                    "cond": {"$eq": ["$$this", "$$this"]}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "first_message": 1,
                        "last_message": 1,
                        "total_reactions": 1,
                        "edited_messages": 1
                    }
                }
            ]
            
            result = await self.messages.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                # Calculate activity metrics
                if stats.get("first_message") and stats.get("last_message"):
                    duration = stats["last_message"] - stats["first_message"]
                    stats["conversation_duration_days"] = duration.days
                    
                    if duration.total_seconds() > 0:
                        stats["messages_per_day"] = stats["total_messages"] / max(duration.days, 1)
                
                return stats
            else:
                return {
                    "total_messages": 0,
                    "unique_sender_count": 0,
                    "unique_senders": [],
                    "message_type_distribution": {},
                    "total_reactions": 0,
                    "edited_messages": 0
                }
                
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {}
    
    async def get_user_activity_stats(
        self,
        user_id: uuid.UUID,
        time_range: int = 30
    ) -> Dict[str, Any]:
        """
        Get user activity statistics across all conversations.
        
        Args:
            user_id: User UUID
            time_range: Time range in days
            
        Returns:
            User activity statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Optimized aggregation for user activity
            pipeline = [
                {
                    "$match": {
                        "sender_id": str(user_id),
                        "deleted_at": None,
                        "created_at": {"$gte": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "conversation_id": "$conversation_id",
                            "date": {
                                "$dateToString": {
                                    "format": "%Y-%m-%d",
                                    "date": "$created_at"
                                }
                            }
                        },
                        "message_count": {"$sum": 1},
                        "message_types": {"$push": "$type"},
                        "total_reactions_received": {"$sum": {"$size": "$reactions"}}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "conversations_participated": {"$addToSet": "$_id.conversation_id"},
                        "daily_activity": {
                            "$push": {
                                "date": "$_id.date",
                                "messages": "$message_count",
                                "reactions_received": "$total_reactions_received"
                            }
                        },
                        "total_messages": {"$sum": "$message_count"},
                        "total_reactions_received": {"$sum": "$total_reactions_received"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "conversations_count": {"$size": "$conversations_participated"},
                        "conversations_participated": 1,
                        "total_messages": 1,
                        "total_reactions_received": 1,
                        "daily_activity": 1,
                        "average_messages_per_day": {
                            "$divide": ["$total_messages", time_range]
                        }
                    }
                }
            ]
            
            result = await self.messages.aggregate(pipeline).to_list(length=1)
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Error getting user activity stats: {e}")
            return {}
    
    async def get_trending_conversations(
        self,
        limit: int = 10,
        time_range: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get trending conversations based on activity.
        
        Args:
            limit: Number of conversations to return
            time_range: Time range in days
            
        Returns:
            List of trending conversations
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range)
            
            # Optimized aggregation for trending conversations
            pipeline = [
                {
                    "$match": {
                        "deleted_at": None,
                        "created_at": {"$gte": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$conversation_id",
                        "message_count": {"$sum": 1},
                        "unique_participants": {"$addToSet": "$sender_id"},
                        "total_reactions": {"$sum": {"$size": "$reactions"}},
                        "last_activity": {"$max": "$created_at"}
                    }
                },
                {
                    "$project": {
                        "conversation_id": "$_id",
                        "message_count": 1,
                        "participant_count": {"$size": "$unique_participants"},
                        "total_reactions": 1,
                        "last_activity": 1,
                        "activity_score": {
                            "$add": [
                                "$message_count",
                                {"$multiply": ["$total_reactions", 2]},
                                {"$multiply": [{"$size": "$unique_participants"}, 3]}
                            ]
                        }
                    }
                },
                {"$sort": {"activity_score": -1}},
                {"$limit": limit}
            ]
            
            return await self.messages.aggregate(pipeline).to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Error getting trending conversations: {e}")
            return []
    
    async def get_message_frequency_analysis(
        self,
        conversation_id: uuid.UUID,
        interval: str = "hour"  # hour, day, week
    ) -> List[Dict[str, Any]]:
        """
        Analyze message frequency patterns.
        
        Args:
            conversation_id: Conversation UUID
            interval: Time interval for grouping
            
        Returns:
            Message frequency data
        """
        try:
            # Define date format based on interval
            date_formats = {
                "hour": "%Y-%m-%d %H:00",
                "day": "%Y-%m-%d",
                "week": "%Y-W%U"
            }
            
            date_format = date_formats.get(interval, "%Y-%m-%d %H:00")
            
            pipeline = [
                {
                    "$match": {
                        "conversation_id": str(conversation_id),
                        "deleted_at": None
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "period": {
                                "$dateToString": {
                                    "format": date_format,
                                    "date": "$created_at"
                                }
                            }
                        },
                        "message_count": {"$sum": 1},
                        "unique_senders": {"$addToSet": "$sender_id"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "period": "$_id.period",
                        "message_count": 1,
                        "unique_sender_count": {"$size": "$unique_senders"}
                    }
                },
                {"$sort": {"period": 1}}
            ]
            
            return await self.messages.aggregate(pipeline).to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error analyzing message frequency: {e}")
            return []
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get database performance metrics for messages collection.
        
        Returns:
            Performance metrics
        """
        try:
            # Collection stats
            stats = await self.db.command("collStats", "messages")
            
            # Index usage stats
            index_stats = await self.messages.aggregate([
                {"$indexStats": {}}
            ]).to_list(length=None)
            
            # Query performance hints
            performance_metrics = {
                "collection_stats": {
                    "total_documents": stats.get("count", 0),
                    "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
                    "index_size_mb": round(stats.get("totalIndexSize", 0) / (1024 * 1024), 2),
                    "average_document_size": round(stats.get("avgObjSize", 0), 2)
                },
                "index_usage": [
                    {
                        "name": idx.get("name"),
                        "accesses": idx.get("accesses", {}).get("ops", 0),
                        "since": idx.get("accesses", {}).get("since")
                    }
                    for idx in index_stats
                ],
                "recommendations": []
            }
            
            # Add performance recommendations
            if stats.get("count", 0) > 100000:  # Large collection
                performance_metrics["recommendations"].append({
                    "type": "indexing",
                    "message": "Consider compound indexes for frequent query patterns",
                    "priority": "high"
                })
            
            if stats.get("storageSize", 0) > 100 * 1024 * 1024:  # >100MB
                performance_metrics["recommendations"].append({
                    "type": "archiving",
                    "message": "Consider archiving old messages to reduce collection size",
                    "priority": "medium"
                })
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def optimize_queries(self) -> Dict[str, Any]:
        """
        Create optimized indexes for common query patterns.
        
        Returns:
            Optimization results
        """
        try:
            optimizations = []
            
            # Common query patterns and their optimal indexes
            indexes_to_create = [
                # Conversation messages with pagination
                {
                    "keys": [("conversation_id", 1), ("deleted_at", 1), ("_id", -1)],
                    "name": "conversation_messages_optimized"
                },
                # User activity queries
                {
                    "keys": [("sender_id", 1), ("created_at", -1)],
                    "name": "user_activity_optimized"
                },
                # Read status queries
                {
                    "keys": [("conversation_id", 1), ("read_by.user_id", 1)],
                    "name": "read_status_optimized"
                },
                # Search queries
                {
                    "keys": [("conversation_id", 1), ("content", "text")],
                    "name": "message_search_optimized"
                },
                # Analytics queries
                {
                    "keys": [("created_at", -1), ("conversation_id", 1), ("deleted_at", 1)],
                    "name": "analytics_optimized"
                }
            ]
            
            for index_spec in indexes_to_create:
                try:
                    # Check if index already exists
                    existing_indexes = await self.messages.list_indexes().to_list(length=None)
                    index_names = [idx["name"] for idx in existing_indexes]
                    
                    if index_spec["name"] not in index_names:
                        await self.messages.create_index(
                            index_spec["keys"],
                            name=index_spec["name"],
                            background=True
                        )
                        optimizations.append({
                            "type": "index_created",
                            "name": index_spec["name"],
                            "status": "success"
                        })
                    else:
                        optimizations.append({
                            "type": "index_exists",
                            "name": index_spec["name"],
                            "status": "skipped"
                        })
                        
                except Exception as e:
                    optimizations.append({
                        "type": "index_failed",
                        "name": index_spec["name"],
                        "error": str(e),
                        "status": "failed"
                    })
            
            return {
                "optimizations": optimizations,
                "total_attempted": len(indexes_to_create),
                "successful": len([o for o in optimizations if o["status"] == "success"]),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error optimizing queries: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_data(
        self,
        days_to_keep: int = 365,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up old message data for performance.
        
        Args:
            days_to_keep: Number of days of data to keep
            dry_run: Whether to perform actual deletion
            
        Returns:
            Cleanup results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Find old messages
            old_messages_query = {
                "created_at": {"$lt": cutoff_date},
                "deleted_at": {"$ne": None}  # Only clean up already soft-deleted messages
            }
            
            old_count = await self.messages.count_documents(old_messages_query)
            
            if dry_run:
                return {
                    "dry_run": True,
                    "messages_to_cleanup": old_count,
                    "cutoff_date": cutoff_date,
                    "estimated_space_freed_mb": old_count * 0.001  # Rough estimate
                }
            else:
                # Perform actual cleanup
                result = await self.messages.delete_many(old_messages_query)
                
                return {
                    "dry_run": False,
                    "messages_cleaned": result.deleted_count,
                    "cutoff_date": cutoff_date,
                    "cleanup_timestamp": datetime.utcnow()
                }
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return {"error": str(e)} 