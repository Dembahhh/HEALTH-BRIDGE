"""
Guideline Indexer

Script to index health guideline documents into ChromaDB.
Processes WHO and local MoH documents for RAG retrieval.

Usage:
    python -m app.core.rag.indexer

This will index all documents in data/guidelines/ into ChromaDB.
"""

import os
from pathlib import Path
from typing import List, Optional

from app.core.rag.chunker import DocumentChunker
from app.core.rag.retriever import VectorRetriever
from app.config.settings import settings


# Sample guideline content for demo purposes
# In production, load from actual PDF/text files
SAMPLE_GUIDELINES = {
    "who_hypertension_diet": {
        "condition": "hypertension",
        "topic": "diet",
        "source": "WHO",
        "content": """
# Dietary Recommendations for Hypertension Prevention

## Salt Reduction
The WHO recommends reducing sodium intake to less than 2 grams per day (equivalent to 5 grams of salt per day) for adults.

High salt intake is directly linked to elevated blood pressure. Practical ways to reduce salt:
- Avoid adding salt at the table
- Use herbs and spices instead of salt for flavoring
- Choose fresh foods over processed foods which often contain hidden salt
- Read food labels and choose lower sodium options
- Limit consumption of salty snacks, processed meats, and canned foods

## Potassium Intake
Increase potassium intake through fresh fruits and vegetables. Potassium helps counteract the effects of sodium.

Good sources of potassium:
- Bananas
- Oranges
- Tomatoes
- Potatoes
- Leafy green vegetables
- Beans and lentils

## DASH Diet Principles
The Dietary Approaches to Stop Hypertension (DASH) diet emphasizes:
- Fruits and vegetables (4-5 servings each per day)
- Whole grains
- Low-fat dairy products
- Lean meats, fish, and poultry
- Nuts and legumes
- Limited saturated fats and sweets

## Low-Cost Alternatives for Low-Resource Settings
When fresh produce is limited or expensive:
- Focus on locally available seasonal vegetables
- Dried beans and lentils are affordable potassium sources
- Traditional fermented foods without added salt
- Grow your own vegetables if space permits
""",
    },
    "who_hypertension_activity": {
        "condition": "hypertension",
        "topic": "activity",
        "source": "WHO",
        "content": """
# Physical Activity Guidelines for Hypertension Prevention

## Recommended Activity Levels
Adults should aim for at least 150 minutes of moderate-intensity physical activity per week, or 75 minutes of vigorous activity.

Regular physical activity can lower systolic blood pressure by 5-8 mmHg in adults with hypertension.

## Types of Beneficial Exercise
- Aerobic exercise: walking, cycling, swimming, dancing
- Resistance training: 2-3 sessions per week
- Flexibility exercises: stretching, yoga

## Practical Activity Options
For those with time or resource constraints:
- Walking is free and can be done almost anywhere
- Take stairs instead of elevators
- Walk or cycle for short trips instead of driving
- Do household chores actively
- Stand and move during work breaks

## Safety Considerations
When exercise areas are unsafe:
- Exercise during daylight hours
- Find indoor alternatives like home workouts
- Walk in groups with neighbors
- Use workplace or community centers if available
- Consider activities that can be done at home

## Starting Slowly
For sedentary individuals:
- Start with 10 minutes of walking per day
- Gradually increase duration and intensity
- Any movement is better than none
- Break activity into shorter sessions throughout the day

## Warning Signs to Stop Exercise
Stop and seek medical attention if experiencing:
- Chest pain or pressure
- Severe shortness of breath
- Dizziness or fainting
- Irregular heartbeat
""",
    },
    "who_diabetes_diet": {
        "condition": "diabetes",
        "topic": "diet",
        "source": "WHO",
        "content": """
# Dietary Recommendations for Type 2 Diabetes Prevention

## Sugar and Carbohydrate Management
Limit intake of free sugars to less than 10% of total energy intake. This includes:
- Added sugars in foods and drinks
- Sugars in honey, syrups, and fruit juices
- Sugars naturally present in sweetened beverages

## Glycemic Control Through Diet
Choose foods with lower glycemic index:
- Whole grains instead of refined grains
- Legumes and beans
- Non-starchy vegetables
- Nuts and seeds

## Fiber Intake
Increase dietary fiber intake to at least 25-30 grams per day:
- Whole grain cereals and bread
- Fruits with skin
- Vegetables
- Legumes

## Meal Timing and Portions
- Eat regular meals at consistent times
- Control portion sizes
- Avoid skipping meals
- Include protein with each meal to slow glucose absorption

## Beverage Recommendations
- Water is the best choice
- Avoid sugary drinks and sodas
- Limit fruit juice intake
- Unsweetened tea and coffee are acceptable

## Affordable Healthy Options
For low-resource settings:
- Traditional whole grains (millet, sorghum)
- Locally grown vegetables
- Dried beans and lentils
- Limit purchased processed foods
""",
    },
    "who_diabetes_activity": {
        "condition": "diabetes",
        "topic": "activity",
        "source": "WHO",
        "content": """
# Physical Activity for Type 2 Diabetes Prevention and Management

## Benefits of Physical Activity
Regular physical activity:
- Improves insulin sensitivity
- Helps control blood glucose levels
- Assists with weight management
- Reduces cardiovascular risk

## Recommended Activity
Adults should aim for:
- At least 150 minutes of moderate-intensity aerobic activity per week
- Muscle-strengthening activities 2 or more days per week
- Reducing sedentary time

## Types of Beneficial Activities
- Walking briskly
- Cycling
- Swimming
- Dancing
- Gardening
- Household chores done actively

## Timing of Activity
For blood glucose management:
- Exercise after meals when possible (helps lower post-meal glucose)
- Consistent timing helps with routine
- Avoid prolonged periods of sitting

## Low-Cost Activity Options
- Walking in your neighborhood
- Bodyweight exercises at home
- Dancing to music
- Active housework
- Walking to work or market
- Using stairs
""",
    },
    "general_red_flags": {
        "condition": "general_ncd",
        "topic": "red_flags",
        "source": "WHO",
        "content": """
# Warning Signs Requiring Immediate Medical Attention

## Hypertension Emergency Signs
Seek immediate medical care if experiencing:
- Severe headache with confusion or vision changes
- Chest pain or difficulty breathing
- Blood pressure above 180/120 mmHg
- Numbness, weakness, or difficulty speaking
- Severe nosebleed that won't stop

## Diabetes Warning Signs
Seek immediate care for:
- Very high blood sugar symptoms: extreme thirst, frequent urination, confusion
- Very low blood sugar symptoms: shakiness, sweating, confusion, fainting
- Fruity-smelling breath (sign of diabetic ketoacidosis)
- Wounds that won't heal
- Sudden vision changes

## General Cardiovascular Warning Signs
- Chest pain or pressure lasting more than a few minutes
- Pain spreading to arm, jaw, neck, or back
- Sudden difficulty breathing
- Sudden severe headache
- Sudden weakness or numbness on one side of body
- Difficulty speaking or understanding speech
- Sudden vision problems in one or both eyes
- Sudden dizziness or loss of balance

## When to Seek Care vs Emergency
GO TO EMERGENCY:
- Any sudden, severe symptoms
- Chest pain
- Signs of stroke (facial droop, arm weakness, speech problems)
- Difficulty breathing
- Loss of consciousness

SEE A HEALTHCARE PROVIDER SOON:
- Persistent headaches
- Gradually worsening symptoms
- New or changing symptoms
- Difficulty managing condition with current treatment

## Important Disclaimer
This information is for educational purposes only. 
It does not replace professional medical advice.
Always consult a qualified healthcare provider for proper diagnosis and treatment.
""",
    },
    "sdoh_behavior_change": {
        "condition": "general_ncd",
        "topic": "sdoh",
        "source": "MoH",
        "content": """
# Behavior Change Strategies for Low-Resource Settings

## Understanding Barriers
Common barriers in low-resource settings:
- Limited income for healthy food
- Unsafe neighborhoods for exercise
- Long working hours
- Lack of access to healthcare
- Limited health literacy

## Practical Strategies for Limited Resources

### Food on a Budget
- Buy seasonal, local produce
- Grow vegetables if possible
- Use dried beans and lentils (cheaper than meat)
- Cook at home instead of buying prepared foods
- Avoid processed foods and sugary drinks
- Share bulk purchases with neighbors

### Exercise with Constraints
When gyms are unaffordable or areas are unsafe:
- Walk during daylight hours
- Do exercises at home
- Use household items as weights
- Dance indoors
- Exercise with family members
- Find safe spaces like schools or churches

### Time Management
For those with limited time:
- Combine activity with daily tasks
- Take short active breaks at work
- Prepare healthy meals in advance
- Involve family in meal preparation
- Set small, achievable goals

### Building Support
- Connect with community health workers
- Join or start neighborhood health groups
- Share healthy recipes and tips with neighbors
- Make family health a shared goal

## Small Steps Approach
Tiny habits for gradual change:
- Replace one sugary drink with water daily
- Add 5 minutes of walking to your day
- Add one vegetable to one meal
- Take stairs one floor before using elevator
- Stand up every hour if seated at work

## Maintaining Motivation
- Track small victories
- Celebrate improvements
- Focus on how you feel, not just numbers
- Remember why health matters to you
- Connect changes to family wellbeing
""",
    },
}


class GuidelineIndexer:
    """
    Indexes health guideline documents into ChromaDB for RAG retrieval.
    """

    def __init__(self, collection_name: str = "guidelines"):
        """
        Initialize the indexer.
        
        Args:
            collection_name: ChromaDB collection name
        """
        self.chunker = DocumentChunker(
            chunk_overlap=50,
            min_chunk_size=100,
        )
        self.retriever = VectorRetriever(collection_name)

    def index_guideline(
        self,
        content: str,
        condition: str,
        topic: str,
        source: str = "WHO",
        region: Optional[str] = None,
    ) -> int:
        """
        Index a single guideline document.
        
        Args:
            content: Guideline text content
            condition: hypertension, diabetes, general_ncd
            topic: diet, activity, red_flags, sdoh
            source: WHO, MoH, etc.
            region: Optional regional context
            
        Returns:
            Number of chunks indexed
        """
        chunks = self.chunker.chunk_guideline(
            text=content,
            condition=condition,
            topic=topic,
            source=source,
            region=region,
        )
        
        self.retriever.add_chunks(chunks)
        
        return len(chunks)

    def index_sample_guidelines(self) -> dict:
        """
        Index the sample guidelines for demo/testing.
        
        Returns:
            Dictionary with indexing statistics
        """
        total_chunks = 0
        stats = {}
        
        for name, data in SAMPLE_GUIDELINES.items():
            num_chunks = self.index_guideline(
                content=data["content"],
                condition=data["condition"],
                topic=data["topic"],
                source=data["source"],
            )
            stats[name] = num_chunks
            total_chunks += num_chunks
        
        return {
            "total_documents": len(SAMPLE_GUIDELINES),
            "total_chunks": total_chunks,
            "per_document": stats,
        }

    def index_from_directory(
        self,
        directory: str = None,
        condition: str = "general_ncd",
        topic: str = "general",
        source: str = "Unknown",
    ) -> dict:
        """
        Index all text/markdown files from a directory.
        
        Args:
            directory: Path to directory with guideline files
            condition: Default condition tag
            topic: Default topic tag
            source: Default source tag
            
        Returns:
            Dictionary with indexing statistics
        """
        if directory is None:
            directory = os.path.join(
                settings.CHROMA_PERSIST_DIR, "..", "guidelines"
            )
        
        directory = Path(directory)
        if not directory.exists():
            return {"error": f"Directory not found: {directory}"}
        
        stats = {}
        total_chunks = 0
        
        for file_path in directory.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            
            num_chunks = self.index_guideline(
                content=content,
                condition=condition,
                topic=topic,
                source=source,
            )
            
            stats[file_path.name] = num_chunks
            total_chunks += num_chunks
        
        for file_path in directory.glob("*.txt"):
            content = file_path.read_text(encoding="utf-8")
            
            num_chunks = self.index_guideline(
                content=content,
                condition=condition,
                topic=topic,
                source=source,
            )
            
            stats[file_path.name] = num_chunks
            total_chunks += num_chunks
        
        return {
            "directory": str(directory),
            "files_processed": len(stats),
            "total_chunks": total_chunks,
            "per_file": stats,
        }

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return self.retriever.get_collection_stats()

    def clear(self) -> None:
        """Clear all indexed documents."""
        self.retriever.clear_collection()


def main():
    """Run the indexer to populate ChromaDB with sample guidelines."""
    print("🏥 Health-bridge AI Guideline Indexer")
    print("=" * 50)
    
    indexer = GuidelineIndexer()
    
    # Clear existing data
    print("\n📋 Clearing existing index...")
    indexer.clear()
    
    # Index sample guidelines
    print("\n📚 Indexing sample guidelines...")
    stats = indexer.index_sample_guidelines()
    
    print(f"\n✅ Indexing complete!")
    print(f"   Documents: {stats['total_documents']}")
    print(f"   Chunks: {stats['total_chunks']}")
    
    print("\n📊 Per-document breakdown:")
    for name, count in stats["per_document"].items():
        print(f"   - {name}: {count} chunks")
    
    # Verify
    print("\n🔍 Verification:")
    collection_stats = indexer.get_stats()
    print(f"   Collection: {collection_stats['name']}")
    print(f"   Total documents: {collection_stats['count']}")
    
    print("\n✨ Done! Guidelines are ready for RAG queries.")


if __name__ == "__main__":
    main()
