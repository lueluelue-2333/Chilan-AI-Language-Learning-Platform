import { useEffect } from 'react';
import apiClient from '../../../../api/apiClient';

export default function usePracticeKnowledgeDetails({ feedback, currentQuestion, setKnowledgeDetails }) {
    useEffect(() => {
        if (!feedback || !currentQuestion?.item_id) {
            setKnowledgeDetails(null);
            return;
        }

        const fetchKnowledge = async () => {
            try {
                const res = await apiClient.get('/study/knowledge', {
                    params: { item_id: currentQuestion.item_id }
                });
                setKnowledgeDetails(res.data?.data || null);
            } catch (e) {
                console.error('加载动态知识点失败:', e);
                setKnowledgeDetails(null);
            }
        };

        fetchKnowledge();
    }, [feedback, currentQuestion, setKnowledgeDetails]);
}
